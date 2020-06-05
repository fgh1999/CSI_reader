import numpy as np
import math
from Bfee import Bfee

def get_scale_csi(bfee: Bfee):
    csi = bfee.csi
    # Calculate the scale factor between normalized CSI and RSSI (mW)
    csi_sq = np.multiply(csi, np.conj(csi)).real
    csi_pwr = np.sum(csi_sq, axis=0)
    csi_pwr = csi_pwr.reshape(1, csi_pwr.shape[0], -1)
    rssi_pwr = dbinv(get_total_rss(bfee))

    scale = rssi_pwr / (csi_pwr / 30)

    if bfee.noise == -127:
        noise_db = -92
    else:
        noise_db = bfee.noise
    thermal_noise_pwr = dbinv(noise_db)

    quant_error_pwr = scale * (bfee.Nrx * bfee.Ntx)

    total_noise_pwr = thermal_noise_pwr + quant_error_pwr
    ret = csi * np.sqrt(scale / total_noise_pwr)
    if bfee.Ntx == 2:
        ret *= math.sqrt(2)
    elif bfee.Ntx == 3:
        ret *= math.sqrt(dbinv(4.5))
    return ret

def get_total_rss(bfee: Bfee):
    # Careful here: rssis could be zero
    rssi_mag = 0
    if bfee.rssi_a != 0:
        rssi_mag += dbinv(bfee.rssi_a)
    if bfee.rssi_b != 0:
        rssi_mag += dbinv(bfee.rssi_b)
    if bfee.rssi_c != 0:
        rssi_mag += dbinv(bfee.rssi_c)
    return db(rssi_mag) - 44 - bfee.agc

def dbinv(x):
    return math.pow(10, x / 10) # 求db的逆过程 分贝毫瓦？

def db(X):
    assert X >= 0
    return (10 * math.log10(X) + 300) - 300
