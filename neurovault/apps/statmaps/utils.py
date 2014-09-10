import os
import tempfile
import subprocess
import shutil
import numpy as np
import string
import random
from .models import Collection


# see CollectionRedirectMiddleware
class HttpRedirectException(Exception):
    pass


def split_filename(fname):
    """Split a filename into parts: path, base filename and extension.

    Parameters
    ----------
    fname : str
        file or path name

    Returns
    -------
    pth : str
        base path from fname
    fname : str
        filename from fname, without extension
    ext : str
        file extension from fname

    Examples
    --------
    >>> from nipype.utils.filemanip import split_filename
    >>> pth, fname, ext = split_filename('/home/data/subject.nii.gz')
    >>> pth
    '/home/data'

    >>> fname
    'subject'

    >>> ext
    '.nii.gz'

    """

    special_extensions = [".nii.gz", ".tar.gz"]

    if fname and fname.endswith(os.path.sep):
        fname = fname[:-1]

    pth, fname = os.path.split(fname)

    ext = None
    for special_ext in special_extensions:
        ext_len = len(special_ext)
        if (len(fname) > ext_len) and \
                (fname[-ext_len:].lower() == special_ext.lower()):
            ext = fname[-ext_len:]
            fname = fname[:-ext_len]
            break
    if not ext:
        fname, ext = os.path.splitext(fname)

    return pth, fname, ext


def generate_pycortex_dir(nifti_file, output_dir, transform_name):
    import cortex
    temp_dir = tempfile.mkdtemp()
    try:
        new_mni_dat = os.path.join(temp_dir, "mni152reg.dat")
        mni_mat = os.path.join(temp_dir, "mni152reg.mat")
        reference = os.path.join(os.environ['FREESURFER_HOME'], 'subjects', 'fsaverage', 'mri', 'brain.mgz')
        shutil.copy(os.path.join(os.environ['FREESURFER_HOME'], 'average', 'mni152.register.dat'), new_mni_dat)
        #this avoids problems with white spaces in file names
        tmp_link = os.path.join(temp_dir, "tmp.nii.gz")
        os.symlink(nifti_file, tmp_link)
        os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"
        exit_code = subprocess.call([os.path.join(os.environ['FREESURFER_HOME'],"bin", "tkregister2"),
                                     "--mov",
                                     tmp_link,
                                     "--targ",
                                     reference,
                                     "--reg",
                                     new_mni_dat,
                                     "--noedit",
                                     "--nofix",
                                     "--fslregout",
                                     mni_mat])
        if exit_code:
            raise RuntimeError("tkregister2 exited with status %d"%exit_code)
        x = np.loadtxt(mni_mat)
        xfm = cortex.xfm.Transform.from_fsl(x, nifti_file, reference)
        xfm.save("fsaverage", transform_name,'coord')
        dv = cortex.DataView((nifti_file, "fsaverage", transform_name))
        cortex.webgl.make_static(output_dir, dv)
    finally:
        shutil.rmtree(temp_dir)


def generate_url_token(length=8):
    chars = string.ascii_uppercase
    token = ''.join(random.choice(chars) for v in range(length))
    if Collection.objects.filter(private_token=token).exists():
        return generate_url_token()
    else:
        return token

