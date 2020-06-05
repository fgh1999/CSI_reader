from Bfee import Bfee
import os


class CSVConverter:
    
    @staticmethod
    def headstr(sample: Bfee):
        sample_csi_shape = sample.csi.shape
        head = ["timestamp_low"]

        # CSI
        for i in range(sample_csi_shape[0]):
            for j in range(sample_csi_shape[1]):
                for k in range(sample_csi_shape[2]):
                    head.append("csi[{} {} {}]".format(i, j, k))

        # RSSI
        head.append("rssi_a")
        head.append("rssi_b")
        head.append("rssi_c")

        # AGC
        head.append("agc")
        return ','.join(head) + '\n'

    @staticmethod
    def dataline(bfee: Bfee):
        csi_shape = bfee.csi.shape
        data = list()
        data.append(str(bfee.timestamp_low))

        # CSI
        for i in range(csi_shape[0]):
            for j in range(csi_shape[1]):
                for k in range(csi_shape[2]):
                    data.append(str(bfee.csi[i, j, k])[1:-1])
        
        # RSSI
        data.append(str(bfee.rssi_a))
        data.append(str(bfee.rssi_b))
        data.append(str(bfee.rssi_c))

        # AGC
        data.append(str(bfee.agc))
        return ','.join(data) + '\n'

    @staticmethod
    def dumpIntoCSV(bfees, file_name = "./dump.csv", maxLimitN=0, timeCount=False):
        # bfees: bfee数据列表
        # file_name: 写出文件名称
        # maxLimitN: 写出记录最大条数限制。如果为0，则不限制
        # timeCount: 是否对该dump过程计时

        assert len(bfees) >= 1
        assert type(bfees[0]) == Bfee
        assert maxLimitN >= 0
        assert not os.path.isfile(file_name), "File already exists"

        if timeCount:
            import time
            time_sta = time.time()

        maxLimitN = len(bfees) if maxLimitN == 0 else min(maxLimitN, len(bfees))
        counter = 0

        with open(file_name, "w") as file:
            file.write(CSVConverter.headstr(bfees[0]))
            for bfee in bfees:
                file.write(CSVConverter.dataline(bfee))

        if timeCount:
            time_end = time.time()
            print("time cost of CSV dump:", time_end - time_sta, "s")
        
    @staticmethod
    def printHead(bfees):
        # bfees: bfee数据列表
        assert len(bfees) >= 1
        assert type(bfees[0]) == Bfee

        print(CSVConverter.headstr(bfees[0]))
        length = min(3, len(bfees))
        for i in range(length):
            print(CSVConverter.dataline(bfees[i]))