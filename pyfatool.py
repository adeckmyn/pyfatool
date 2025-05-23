#! /usr/bin/env python3
# basic FA utilities combined in 1 call
# Alex Deckmyn, KMI, 2024
import sys
import struct
import os
import argparse
#import math
import datetime
import re

parser = argparse.ArgumentParser(prog="pyfatool")
current_wdir = os.getcwd()
__version__ = "0.1.1"
__date__ = "24/04/2025"

parser.add_argument("fafile", 
        help="/path/to/file",
        nargs = "?",
        )
parser.add_argument('-p', # 'prod',
    help="production date/time",
    action = 'store_true',
    )
parser.add_argument('-l',# 'ls',
    help="list fields",
    action = 'store_true',
    )
parser.add_argument('-s',# 'size',
    help="expected file size",
    action = 'store_true',
    )
parser.add_argument('-H',# 'header',
    help="FA header",
    action = 'store_true',
    )
parser.add_argument('-F',
    help="fix frame parameter in recent Arpege LBC's",
    action = 'store_true',
    )
parser.add_argument('-q',  # 'humi'
    help="check whether specific humidity is spectral or grid point",
    action = 'store_true',
    )
parser.add_argument('-d',  # 'date/time'
    help="forecast date and lead time",
    action = 'store_true',
    )
# TODO: add options "D1", "D2" for more details
parser.add_argument('-D',  # 'domain'
    help="model domain",
    action = 'store_true',
    )

parser.add_argument('-v',  # 'version'
    help="version",
    action = 'store_true',
    )
args = parser.parse_args()

def get_header(fafile):
    # read the first sector : 22 big-endian long integers
    # the end of this sector may also contain the locations of
    # additional index sectors
    fafile.seek(0)
    h22 = list(struct.unpack(">22Q", fafile.read(22*8)))
    header = { 
          'sector_size'   : h22[0] , # sector size given in 8 byte words
          'name_length'   : h22[1] , # should always be 16
          'closure'       : h22[2] , # should be 0
          'header_len'    : h22[3] , # should be 22
          'nsectors'      : h22[4] , # >=4
          'nrecords'      : h22[5] , # total nr of records in index (some may be empty)
          'minlen'        : h22[6] , # shortest data record (1 for FA files)
          'maxlen'        : h22[7] , # longest data record
          'datalen'       : h22[8] , # total length of data records
          'nrewr_same'    : h22[9] , # rewrites same length
          'nrewr_shorter' : h22[10] , # rewrites shorter (small data hole)
          'nrewr_longer'  : h22[11] , # rewrites longer (-> leaves hole in index)
          'n_rec_seq'     : h22[12] , # records per index sequence=sector_size/2
          'creation_date' : h22[13] ,
          'creation_time' : h22[14] ,
          'last_mod_date' : h22[15] ,
          'last_mod_time' : h22[16] ,
          'first_mod_date': h22[17] ,
          'first_mod_time': h22[18] ,
          'n_index'       : h22[19] , # nr of index sectors, ==1 even if there are more???
          'nholes'        : h22[20] , # nr of "holes" in the index
          'max_sectors'   : h22[21]   # nr data sectors used
          }
    # NOTE: maybe n_index > 1 means you have 2 consecutive index sectors,
    #       so doubling n_req_seq
    #       but I have never encountered such a file...
    if header['name_length'] != 16 or header['header_len'] != 22:
        print('ERROR: not a regular FA file.')
        exit(1)
    # now we build a list of index sectors
    # first index starts in 2nd sector
    if header['nrecords'] <= header['n_rec_seq']:
        header['index_list'] = [ [ 1, header['nrecords'] ] ]
    else:
        # multiple name & address sectors
        n_index = header['nrecords'] // header['n_rec_seq']
        fafile.seek( 8*(header['sector_size'] - n_index) )
        indlist = list(struct.unpack(">%iQ"%n_index,fafile.read(n_index*8)))
        # records per index list: only last one may have < n_rec_seq
        ilist =[2] + list(reversed(indlist))
        llist = [ header['n_rec_seq'] for i in range(n_index) ]
        llist.append(header['nrecords'] % header['n_rec_seq'])
        header['index_list'] = [[ ilist[i]-1,llist[i] ] for i in range(n_index+1)  ]
    return(header)

def get_fieldnames(fafile, header=None):
    if header is None:
        header = get_header(fafile)
    fieldnames = []
    nind = len(header['index_list'])
    for i in range(nind):
        ind = header['index_list'][i]
        fafile.seek(ind[0] * 8 * header['sector_size'])
        fieldnames = fieldnames + [ x.decode('ascii') for x in 
            list(struct.unpack("16s"*ind[1], fafile.read(16*ind[1]))) ]
    return(fieldnames)

def get_locations(fafile, header=None):
    # return byte location and data length for all fields
    if header is None:
        header = get_header(fafile)
    nind = len(header['index_list'])
    data_loc = []
    data_len = []
    for i in range(nind):
        ind = header['index_list'][i]
        # FIXME: *maybe* +1 should rather be +header['n_index'] ???
        fafile.seek( (ind[0] + 1) * 8 * header['sector_size'])
        sec3 = struct.unpack(">%iQ"%(2*ind[1]), fafile.read(16*ind[1]) )
        # shift location by one for correct result with seek ()
        # and multiply by 8 for bytes in stead of words
        data_loc = data_loc + [ (x-1)*8 for x in sec3[1::2] ]
        data_len = data_len + [ x*8 for x in sec3[::2] ]
    return(data_loc, data_len)

def get_list(fafile, header=None):
    if header is None:
        header = get_header(fafile)
    fieldnames = get_fieldnames(fafile, header)
    dloc, dlen = get_locations(fafile, header)
    hole_indices = [i for i in range(header['nrecords']) if fieldnames[i]==' '*16]
    if len(hole_indices) != header['nholes']:
        print("ERROR: inconsistent holes in index sector.")
  # NOTE: in python < 3.7, a dictionary may not remain in right order...
    flist = { fieldnames[i]:[ dloc[i], dlen[i] ]
        for i in range(header['nrecords'])
        if i not in hole_indices }
    hlist = { 'h'+str(i+1):[dloc[i],dlen[i]] for i in hole_indices }
    return flist, hlist

def list_fields(fafile, header=None):
    # from file header: section size in 8-byte words
    if header is None:
        header = get_header(fafile)
    flist, hlist = get_list(fafile, header)
    ncol = 3
    fn = list(flist.keys())
    for i in range(0, header['nrecords'] - header['nholes'], ncol):
        print( f"{i+1:4d} : " + "  ".join(fn[i:(i+ncol)]) )

def read_data_field(fafile, dloc):
    # dloc contains data location and length in bytes
    # return raw bytes
    fafile.seek(dloc[0])
    return(fafile.read(dloc[1]))

def get_datetime(fafile, header=None):
    if header is None:
        header = get_header(fafile)
    flist, hlist = get_list(fafile, header)
    df1 = struct.unpack(">11Q", read_data_field(fafile, flist['DATE-DES-DONNEES']))
    # fcdate = datetime.datetime(df1[0], df1[1], df1[2], df1[3], df1[4], 0)
    fcdate = datetime.datetime(df1[0], df1[1], df1[2], 0, 0, 0)
    if 'DATX-DES-DONNEES' in flist.keys():
        # time of day given in seconds
        df2 = struct.unpack(">11Q", read_data_field(fafile, flist['DATX-DES-DONNEES']))
        fcdate = fcdate + datetime.timedelta(seconds = df2[2])
#    print(df1)
#    print(df2)
    else:
        # time of day given in  hh:mm
        df2 = None
        fcdate = fcdate + datetime.timedelta(hours=df1[3], minutes=df1[4])

    # lead time is usually in hours, but not always!
    if df1[5] == 0: # minutes
        lt = f" + {df1[6]} minutes"
    elif df1[5] == 1: # hours
        lt = f" + {df1[6]} hours"
    elif df1[5] == 254: # seconds
        lt = f" + {df1[6]} seconds"
#    lt = str(df2[3]).zfill(2)+" seconds"

#  if not df2 is None :
      # fields 4-5 are P1-P2 in seconds (for time intervals)
#      ss = df2[2] # start of fc: time of day in seconds
#      lt_ss = df2[3] # lead time in seconds
#      tstep = df2[6] # time step in seconds
#  print("{0}-{1}-{2}T{3}:{4}Z + {5}".format(yyyy, mm, dd, rr, MM, lt))
    print(fcdate.strftime("%Y-%m-%dT%H:%MZ") + lt)

def fix_frame(fafile, header=None, frame_name="CADRE-REDPOINPOL", pos=0, new_value=10):
    if header is None:
        header = get_header(fafile)
    flist, hlist = get_list(fafile, header)
    fafile.seek(flist[frame_name][0] + pos*8)
    old_value = struct.unpack(">1Q", fafile.read(8) )
    print(f"old_value: {old_value}")
    print(f"new_value: {new_value}")
    fafile.seek(flist["CADRE-REDPOINPOL"][0] + pos*8)
    fafile.write(struct.pack(">1Q", new_value) )

def find_in_list(flist, templates):
    # return a list (with byte location) of all fields matching a list of templates
    matching = { k:v for k,v in flist.items() if any ( re.search(ttt, k) for ttt in templates ) }
    # read templates from a file (containing a python command templates = [...])
    # exec(open(template_file).read())
    # template may be e.g. [ "^S[0-9]{3}TEMPERATURE", "^SURFPREC" ]
    return(matching)

def check_type(fafile, header=None, field="S001HUMI.SPECIFI"):
    if header is None:
        header = get_header(fafile)
    flist, hlist = get_list(fafile, header)
    try:
        fafile.seek(flist[field][0])
    except:
        print(f"Field {field} not found.")
        return
    ftype = struct.unpack(">%iQ"%(2), fafile.read(16) )
    # second integer = 0 means GP, !=0 means SPEC
    if ftype[1] == 0:
        result = "gp"
    else:
        result = "sp"
    print(result)

def get_domain(fafile, header=None):
    if header is None:
        header = get_header(fafile)
    flist, hlist = get_list(fafile, header)
    # CADRE_DIMENSIONS for grid size & spectral truncation
    #fafile.seek(flist['CADRE_DIMENSIONS'][0])
    nval = 5
    fmt = ">%dq" % nval
    dims = struct.unpack(fmt, read_data_field(fafile, flist['CADRE-DIMENSIONS']))
    result = {
            'NSMAX':dims[0],
            'NDGL':dims[1],
            'NDLON':dims[2],
            'NFLEVG':dims[3],
            }
    if dims[4] < 0:
        # LAM file
        result['lam'] = True
        result['NMSMAX'] = -dims[4]
    else:
        # Arpege file
        result['lam'] = False
        result['NSTTYP'] = dims[4]

    if result['lam']:
        nval = 8 + 2*(result['NSMAX'] + 2)
        fmt = ">%dq" % nval
        dims2 = struct.unpack(fmt, read_data_field(fafile, flist['CADRE-REDPOINPOL']))
        result['SPTRUNC'] = dims2[0]
        # result['E'] = dims2[1]
        result['NDLUX'] = dims2[2]
        result['NDLUN'] = dims2[3]
        result['NDGUX'] = dims2[4]
        result['NDGUN'] = dims2[5]
        result['IX'] = dims2[6]
        result['IY'] = dims2[7]

        nval = 18
        fmt = ">%dd" % nval
        proj = struct.unpack(fmt, read_data_field(fafile, flist['CADRE-SINLATITUD']))
        #print(proj)

    # TODO: print a *clean & readable* summary
    print(result)


def main():
    if args.v:
        print(f"pyfatool version: {__version__} ({__date__})")
        return
    fname = args.fafile
    if fname is None:
        print(f"ERROR: no file name given.")
        parser.print_usage()
        return
    if not os.path.exists(fname):
        print(f"ERROR: file {fname} not found.")
        exit(1)
    if args.F:
        fmode = 'rb+'
    else:
        fmode = 'rb'
    with open(fname, fmode) as fafile:
        header = get_header(fafile)
        if args.H:
            print(header)
        if args.p:
            print(f"Creation: {header['creation_date']:08d} : {header['creation_time']:06d}")
            print(f"Last mod: {header['last_mod_date']:08d} : {header['last_mod_time']:06d}")
        if args.s:
            expected_size = 8 * header['sector_size'] * header['nsectors']
            real_size = os.stat(fname).st_size
            if expected_size != real_size:
                print(f"ERROR : expected {expected_size}, actual size {real_size}.")
                exit(1)
            else:
                print(f"OK : size {real_size}")
        if args.l:
            list_fields(fafile, header)
        if args.d:
            get_datetime(fafile, header)
        if args.q:
            check_type(fafile, header, 'S001HUMI.SPECIFI')
        if args.F:
            fix_frame(fafile, header, 'CADRE-REDPOINPOL', 0, 10)
        if args.D:
            get_domain(fafile, header)

if __name__ == "__main__":
    main()

