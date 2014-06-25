import os
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger('aw-export-fif')

# get filename first
import pyqtgraph as pg

app = pg.mkQApp()
LOG.debug('built QApplication %r', app)

LOG.debug('requesting filename...')
filename = pg.QtGui.QFileDialog.getSaveFileName(
    caption='Choose fif filename to save to',
    filter='Raw FIFF file (*-raw.fif)')
LOG.debug('received %r', filename)

# PySide / PyQt difference, _ would be extension of file chosen?
try:
    filename, _ = filename
except:
    pass

filename = unicode(filename)

if not filename.endswith('-raw.fif'):
    LOG.warning('filename %r does not conform to convention, appending -raw.fif to name')
    filename += '-raw.fif'

if len(filename) == 0:
    LOG.info('filename had zero length, quitting...')

else:
    LOG.debug('beginning imports')
    import time
    tic = time.time()

    import anywave
    import numpy as np

    # add our deps to the beginning of the path
    here = os.path.dirname(os.path.abspath(sys.argv[-1]))
    deps = os.path.join(here, 'deps')
    LOG.debug('inserting custom deps at path %r', deps)
    sys.path.insert(0, deps)

    # import mne stuff
    import mne
    LOG.debug('have mne %r, version %r', mne, mne.__version__)
    from mne.io.array import RawArray
    try:
        from mne.io.meas_info import create_info
    except ImportError:
        from mne.io.array import create_info

    LOG.info('receiving data...')
    channels = anywave.getData(0, -1, 'No Filtering')

    # make sure all channels have same rate and same length
    LOG.info('verifying data...')
    ch0 = channels[0]
    assert all(ch0['sampling_rate'] == ch['sampling_rate'] for ch in channels)
    assert all(ch0['data'].shape == ch['data'].shape for ch in channels)
    sfreq = ch0['sampling_rate']
    nsamp = ch0['data'].shape[0]
    nchan = len(channels)
    LOG.info('received %d channels, %dk samples @ %.3f Hz', nchan, nsamp/1000, sfreq)
    LOG.info('data array will required %.3fMB of memory', (nsamp * nchan) * 4 / 2**20.0)

    LOG.info('building data array, labels & types')
    data = np.zeros((nchan, nsamp), np.float32)
    labels = []
    types = []
    for i, chan in enumerate(channels):
        label = chan['name']
        # bipolar case
        if chan['ref']:
            label += '-' + chan['ref']
        LOG.debug('channel %03d %r%s', i, label, ' bipolar' if chan['ref'] else '')
        data[i] = chan['data']
        labels.append(label)
        types.append('eeg')

    LOG.info('building mne raw instance...')
    info = create_info(labels, sfreq, types)
    raw = RawArray(data, info)
    LOG.info('%r', raw)

    LOG.info('saving to %r', filename)
    raw.save(filename)
    LOG.info('done in %.3f s', time.time() - tic)
