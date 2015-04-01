#!/usr/bin/env python
import os, glob, shutil

# settings
file_glob = 'P_RCP_85_*/*/*%s*.%s'
spec_file_glob = 'P_RCP_85_Annual/renders/P_RCP_85_Annual__*__P2041_2070.png' 

renders_out_dir = 'renders'
renders_and_data_out_dir = 'renders_and_data'

# logic
def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def list_boundaries(outform):
    return map(lambda x: x.split('__')[1], glob.glob(outform))

def copy_files(bounds, target, ext):
    mkdir(target)
    for bound in bounds:
        bound_dir = '%s/%s' % (target, bound)
        mkdir(bound_dir)
        src_files = glob.glob(file_glob % (bound, ext))
        for src_file in src_files:
            shutil.copyfile(src_file, '%s/%s' % (bound_dir, os.path.basename(src_file)))

# go!
bnds = list_boundaries(spec_file_glob)
copy_files(bnds, renders_out_dir, 'png')
copy_files(bnds, renders_and_data_out_dir, '*')
