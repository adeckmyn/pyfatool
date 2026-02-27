# pyfatool
Very basic python script for analysing FA files.

## Basics
This simple script can help for a quick look at an FA file. Note that there are a few options (`--mp`) that actually *modify* the file. All others are totally harmless.

## Install
This script is a single executable file that doesn't require any installation.
Just copy/link the single script file to wherever you want.

## Run
```
pyfatool <options> <FA file>
```
## Options
* `-d` : return forecast date and lead time of the file
* `-p` : return date/time of production and last modification
* `-l` : list fields in the FA file (including domain discription sectors)
* `-s` : expected and actual file size (for checking e.g. completeness after transfer)
* `-H` : FA header sector
* `-q` : check whether specific humidity is spectral (alaro) or grid point (arome)
* `-D` : return basic domain info
* `--mp` : Modify a single frame parameter
* `--mn` : Modify a field name (--mn <oldname> <newname>)
* `--md` : Modify date/time    (not yet implemented)
* `--version` : version info
* `-h` : help



