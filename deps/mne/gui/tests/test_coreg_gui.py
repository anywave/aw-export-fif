# Author: Christian Brodbeck <christianbrodbeck@nyu.edu>
#
# License: BSD (3-clause)

from ...externals.six import string_types
import os

import numpy as np
from numpy.testing import assert_allclose, assert_array_equal
from nose.tools import (assert_equal, assert_almost_equal, assert_false,
                        assert_raises, assert_true)

import mne
from mne.datasets import sample
from mne.io.kit.tests import data_dir as kit_data_dir
from mne.utils import _TempDir, requires_traits, requires_mne_fs_in_env


data_path = sample.data_path(download=False)
raw_path = os.path.join(data_path, 'MEG', 'sample', 'sample_audvis_raw.fif')
kit_raw_path = os.path.join(kit_data_dir, 'test_bin.fif')
subjects_dir = os.path.join(data_path, 'subjects')

tempdir = _TempDir()

trans_dst = os.path.join(tempdir, 'test-trans.fif')


@sample.requires_sample_data
@requires_traits
def test_coreg_model():
    """Test CoregModel"""
    from mne.gui._coreg_gui import CoregModel

    model = CoregModel()
    assert_raises(RuntimeError, model.save_trans, 'blah.fif')

    model.mri.subjects_dir = subjects_dir
    model.mri.subject = 'sample'

    assert_false(model.mri.fid_ok)
    model.mri.lpa = [[-0.06, 0, 0]]
    model.mri.nasion = [[0, 0.05, 0]]
    model.mri.rpa = [[0.08, 0, 0]]
    assert_true(model.mri.fid_ok)

    model.hsp.file = raw_path
    assert_allclose(model.hsp.lpa, [[-7.137e-2, 0, 5.122e-9]], 1e-4)
    assert_allclose(model.hsp.rpa, [[+7.527e-2, 0, 5.588e-9]], 1e-4)
    assert_allclose(model.hsp.nasion, [[+3.725e-9, 1.026e-1, 4.191e-9]], 1e-4)
    assert_true(model.has_fid_data)

    lpa_distance = model.lpa_distance
    nasion_distance = model.nasion_distance
    rpa_distance = model.rpa_distance
    avg_point_distance = np.mean(model.point_distance)

    model.fit_auricular_points()
    old_x = lpa_distance ** 2 + rpa_distance ** 2
    new_x = model.lpa_distance ** 2 + model.rpa_distance ** 2
    assert_true(new_x < old_x)

    model.fit_fiducials()
    old_x = lpa_distance ** 2 + rpa_distance ** 2 + nasion_distance ** 2
    new_x = (model.lpa_distance ** 2 + model.rpa_distance ** 2
             + model.nasion_distance ** 2)
    assert_true(new_x < old_x)

    model.fit_hsp_points()
    assert_true(np.mean(model.point_distance) < avg_point_distance)

    model.save_trans(trans_dst)
    trans = mne.read_trans(trans_dst)
    assert_allclose(trans['trans'], model.head_mri_trans)

    # test restoring trans
    x, y, z, rot_x, rot_y, rot_z = .1, .2, .05, 1.5, 0.1, -1.2
    model.trans_x = x
    model.trans_y = y
    model.trans_z = z
    model.rot_x = rot_x
    model.rot_y = rot_y
    model.rot_z = rot_z
    trans = model.head_mri_trans
    model.reset_traits(["trans_x", "trans_y", "trans_z", "rot_x", "rot_y",
                        "rot_z"])
    assert_equal(model.trans_x, 0)
    model.set_trans(trans)
    assert_almost_equal(model.trans_x, x)
    assert_almost_equal(model.trans_y, y)
    assert_almost_equal(model.trans_z, z)
    assert_almost_equal(model.rot_x, rot_x)
    assert_almost_equal(model.rot_y, rot_y)
    assert_almost_equal(model.rot_z, rot_z)

    # info
    assert_true(isinstance(model.fid_eval_str, string_types))
    assert_true(isinstance(model.points_eval_str, string_types))


@sample.requires_sample_data
@requires_traits
@requires_mne_fs_in_env
def test_coreg_model_with_fsaverage():
    """Test CoregModel"""
    from mne.gui._coreg_gui import CoregModel

    mne.create_default_subject(subjects_dir=tempdir)

    model = CoregModel()
    model.mri.subjects_dir = tempdir
    model.mri.subject = 'fsaverage'
    assert_true(model.mri.fid_ok)

    model.hsp.file = raw_path
    lpa_distance = model.lpa_distance
    nasion_distance = model.nasion_distance
    rpa_distance = model.rpa_distance
    avg_point_distance = np.mean(model.point_distance)

    # test hsp point omission
    model.trans_y = -0.008
    model.fit_auricular_points()
    model.omit_hsp_points(0.02)
    assert_equal(model.hsp.n_omitted, 1)
    model.omit_hsp_points(reset=True)
    assert_equal(model.hsp.n_omitted, 0)
    model.omit_hsp_points(0.02, reset=True)
    assert_equal(model.hsp.n_omitted, 1)

    # scale with 1 parameter
    model.n_scale_params = 1

    model.fit_scale_auricular_points()
    old_x = lpa_distance ** 2 + rpa_distance ** 2
    new_x = model.lpa_distance ** 2 + model.rpa_distance ** 2
    assert_true(new_x < old_x)

    model.fit_scale_fiducials()
    old_x = lpa_distance ** 2 + rpa_distance ** 2 + nasion_distance ** 2
    new_x = (model.lpa_distance ** 2 + model.rpa_distance ** 2
             + model.nasion_distance ** 2)
    assert_true(new_x < old_x)

    model.fit_scale_hsp_points()
    avg_point_distance_1param = np.mean(model.point_distance)
    assert_true(avg_point_distance_1param < avg_point_distance)

    desc, func, args, kwargs = model.get_scaling_job('test')
    assert_true(isinstance(desc, string_types))
    assert_equal(args[0], 'fsaverage')
    assert_equal(args[1], 'test')
    assert_allclose(args[2], model.scale)
    assert_equal(kwargs['subjects_dir'], tempdir)

    # scale with 3 parameters
    model.n_scale_params = 3
    model.fit_scale_hsp_points()
    assert_true(np.mean(model.point_distance) < avg_point_distance_1param)

    # test switching raw disables point omission
    assert_equal(model.hsp.n_omitted, 1)
    model.hsp.file = kit_raw_path
    assert_equal(model.hsp.n_omitted, 0)
