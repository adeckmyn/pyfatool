# pyfatool
Very basic python script for analysing FA files.

## Basics
This simple script can help for a quick look at an FA file. Note that there is one option (`-F`) that actually *modifies* the file. All others are totally harmless.

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
* `-s` : expected and actual file size (for checking completeness of transfer)
* `-H` : FA header sector
* `-q` : check whether specific humidity is spectral (alaro) or grid point (arome)
* `-F` : Fix a single frame parameter that causes older compilations to fail with recent Arpège LBC's. **NOTE: this is the only option that modifies the file!**
* `-D` : return domain size
* `-h` : help



