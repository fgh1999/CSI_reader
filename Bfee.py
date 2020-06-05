import numpy as np

class Bfee:

    field_len = 0           # uin16: length of {code, field}
    code = 0                # uint8

    # fields
    timestamp_low = 0       # uint32: NIC网卡1MHz时钟的低32位
    bfee_count = 0          # uint16: 驱动记录并发送到用户空间的波束形成测量值的数量
    Nrx = 0                 # uint8: 接收端使用的天线数量
    Ntx = 0                 # uint8: 发送端使用的天线数量
    rssi_a = 0              # uint8: 每个天线由接收端NIC测量出的RSSI值
    rssi_b = 0              # uint8
    rssi_c = 0              # uint8
    noise = 0               # int8: 单位为db
    agc = 0                 # uint8: Automatic Gain Control
    antenna_sel = 0         # uint8
    len = 0                 # uint16
    fake_rate_n_flags = 0   # uint16

    csi = None              # CSI raw data, 30 × Ntx × Nrx complex matrix
    perm = list(range(3))   # 排列方式：展示NIC如何将3个接收天线的信号排列到3个RF链路上

    def to_dict(self):
        bfee_dict = {}
        bfee_dict['timestamp_low'] = self.timestamp_low
        bfee_dict['bfee_count'] = self.bfee_count
        bfee_dict['Nrx'] = self.Nrx
        bfee_dict['Ntx'] = self.Ntx
        bfee_dict['rssi_a'] = self.rssi_a
        bfee_dict['rssi_b'] = self.rssi_b
        bfee_dict['rssi_c'] = self.rssi_c
        bfee_dict['noise'] = self.noise
        bfee_dict['agc'] = self.agc
        bfee_dict['antenna_sel'] = self.antenna_sel
        bfee_dict['perm'] = self.perm
        bfee_dict['len'] = self.len
        bfee_dict['fake_rate_n_flags'] = self.fake_rate_n_flags
        bfee_dict['csi'] = self.csi
        return bfee_dict

    def to_json(self):
        import json

        def complex2str_recursively(target):
            if type(target[0]) != list:
                for i in range(len(target)):
                    target[i] = str(target[i])[1:-1]
            else:
                for i in range(len(target)):
                    complex2str_recursively(target[i])
            return target

        bfee_dict = {}
        bfee_dict['timestamp_low'] = self.timestamp_low
        bfee_dict['rssi_a'] = self.rssi_a
        bfee_dict['rssi_b'] = self.rssi_b
        bfee_dict['rssi_c'] = self.rssi_c
        bfee_dict['agc'] = self.agc
        bfee_dict['csi'] = complex2str_recursively(self.csi.tolist())
        return json.dumps(bfee_dict)

    def to_simple_bytes(self, encoding_order="little"):
        bytes_ = self.timestamp_low.to_bytes(4, encoding_order, signed=False)
        bytes_ += self.rssi_a.to_bytes(1, encoding_order, signed=False)
        bytes_ += self.rssi_b.to_bytes(1, encoding_order, signed=False)
        bytes_ += self.rssi_c.to_bytes(1, encoding_order, signed=False)
        bytes_ += self.agc.to_bytes(1, encoding_order, signed=False)

        shape = self.csi.shape
        for i in range(shape[0]):
            for j in range(shape[1]):
                for k in range(shape[2]):
                    bytes_ += int(self.csi[i, j, k].real).to_bytes(1, 
                                                                   encoding_order, signed=True)
                    bytes_ += int(self.csi[i, j, k].imag).to_bytes(1,
                                                                   encoding_order, signed=True)
        return bytes_


    @staticmethod
    def records_from_offline_file(filename, timeCount=False):
        if timeCount:
            import time
            time_sta = time.time()

        with open(filename, "rb") as f: # 一次将所有的文件内容读取完 => 离线的
            array = f.read()

        res = list()
        file_len = len(array)
        counter = 0
        calc_len = 0

        # Initialize variables
        cur = 0                      # Current offset into file
        broken_perm = 0              # Flag marking whether we've encountered a broken CSI yet
        triangle = [0, 1, 3]         # What perm should sum to for 1,2,3 antennas (0, 1, 2)

        while cur < (file_len - 3):
            bfee = Bfee()

            # Read size and code
            bfee.field_len = int.from_bytes(
                array[cur:cur+2], byteorder='big', signed=False)
            bfee.code = array[cur+2]
            cur += 3

            # there is CSI in field if code == 187，If unhandled code skip (seek over) the record and continue
            if bfee.code != 187:
                cur = cur + bfee.field_len - 1  # skip all other info
                continue

            # get beamforming or phy data
            bfee.timestamp_low = int.from_bytes(
                array[cur:cur+4], byteorder='little', signed=False)
            bfee.bfee_count = int.from_bytes(
                array[cur+4:cur+6], byteorder='little', signed=False)
            bfee.Nrx = array[cur+8]
            bfee.Ntx = array[cur+9]
            bfee.rssi_a = array[cur+10]
            bfee.rssi_b = array[cur+11]
            bfee.rssi_c = array[cur+12]
            bfee.noise = array[cur+13] - 256
            bfee.agc = array[cur+14]
            bfee.antenna_sel = array[cur+15]
            bfee.len = int.from_bytes(
                array[cur+16:cur+18], byteorder='little', signed=False)
            bfee.fake_rate_n_flags = int.from_bytes(
                array[cur+18:cur+20], byteorder='little', signed=False)
            calc_len = (
                30 * (bfee.Nrx * bfee.Ntx * 8 * 2 + 3) + 6) / 8
            bfee.csi = np.zeros(
                shape=(30, bfee.Nrx, bfee.Ntx), dtype=np.dtype(np.complex))
            bfee.perm[0] = (bfee.antenna_sel) & 0x3
            bfee.perm[1] = (bfee.antenna_sel >> 2) & 0x3
            bfee.perm[2] = (bfee.antenna_sel >> 4) & 0x3
            cur += 20

            # get payload
            payload = array[cur:cur+bfee.len]
            cur += bfee.len

            # Check that length matches what it should
            if (bfee.len != calc_len):
                print("MIMOToolbox:read_bfee_new:size",
                        "Wrong beamforming matrix size.")

            # Compute CSI from all this crap
            try:
                index = 0
                for i in range(30):
                    index += 3
                    remainder = index % 8
                    for j in range(bfee.Nrx):
                        for k in range(bfee.Ntx):
                            real_bin = bytes([(payload[int(index / 8)] >> remainder) | (
                                payload[int(index/8+1)] << (8-remainder)) & 0b11111111])
                            real = int.from_bytes(
                                real_bin, byteorder='little', signed=True)
                            imag_bin = bytes([(payload[int(index / 8+1)] >> remainder) | (
                                payload[int(index/8+2)] << (8-remainder)) & 0b11111111])
                            imag = int.from_bytes(
                                imag_bin, byteorder='little', signed=True)
                            tmp = np.complex(float(real), float(imag))
                            bfee.csi[i, j, k] = tmp
                            index += 16
            except:
                print("Illegal data occurred at the {}th bfee".format(counter))
            

            # matrix does not contain default values
            if sum(bfee.perm) != triangle[bfee.Nrx-1]:
                print('WARN ONCE: Found CSI (', filename, ') with Nrx=',
                        bfee.Nrx, ' and invalid perm=[', bfee.perm, ']\n')
            else:
                temp_csi = np.zeros(
                    bfee.csi.shape, dtype=np.dtype(np.complex))
                for r in range(bfee.Nrx):
                    temp_csi[:, bfee.perm[r], :] = bfee.csi[:, r, :]
                bfee.csi = temp_csi

            res.append(bfee)
            counter += 1

        if timeCount:
            time_end = time.time()
            print("time costed during reading data:", time_end - time_sta, "s")
        return res
