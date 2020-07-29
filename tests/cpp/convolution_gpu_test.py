import numpy as np
import unittest
import time

import torch
import MinkowskiEngineTest._C as _C

from utils import load_file, batched_coordinates
from gradcheck import gradcheck


class ConvolutionTestCase(unittest.TestCase):
    def test(self):
        D, IC, OC = 2, 3, 5
        coordinates = torch.IntTensor([[0, 1], [0, 2]]).to(0)
        in_features = torch.rand(len(coordinates), IC).to(0)

        manager = _C.CoordinateMapManager()
        in_key, unique_inverse_map = manager.insert_and_map(coordinates, [1], "")
        kernel_size = [3]
        kernel_stride = [2]
        kernel_dilation = [1]
        out_key = _C.CoordinateMapKey(D)

        # size, in, out
        kernel = torch.rand(3, IC, OC).to(0)

        out_features = _C.ConvolutionForwardGPUf(
            in_features,
            kernel,
            kernel_size,
            kernel_stride,
            kernel_dilation,
            _C.RegionType.HYPER_CUBE,
            torch.IntTensor().to(0),
            in_key,
            out_key,
            manager,
        )

        print(in_features, out_features)

    def test_backward(self):
        IC, OC = 3, 5
        coordinates = torch.IntTensor([[0, 1, -1], [0, 2, 1]]).to(0)
        in_features = torch.rand(len(coordinates), IC).to(0)

        manager = _C.CoordinateMapManager()
        in_key, unique_inverse_map = manager.insert_and_map(coordinates, [1, 1], "")
        kernel_size = [3, 3]
        kernel_stride = [2, 2]
        kernel_dilation = [1, 1]
        out_key = _C.CoordinateMapKey(3)

        # size, in, out
        kernel = torch.rand(9, IC, OC).to(0)

        out_features = _C.ConvolutionForwardGPUf(
            in_features,
            kernel,
            kernel_size,
            kernel_stride,
            kernel_dilation,
            _C.RegionType.HYPER_CUBE,
            torch.IntTensor().to(0),
            in_key,
            out_key,
            manager,
        )

        out_feat_grad = torch.rand_like(out_features)
        in_feat_grad, kernel_grad = _C.ConvolutionBackwardGPUf(
            in_features,
            out_feat_grad,
            kernel,
            kernel_size,
            kernel_stride,
            kernel_dilation,
            _C.RegionType.HYPER_CUBE,
            torch.IntTensor().to(0),
            in_key,
            out_key,
            manager,
        )

        print(in_feat_grad, kernel_grad)

    def test_pcd(self):
        IC, OC = 3, 16
        coords, colors, pcd = load_file("1.ply")
        kernel_size = [3, 3, 3]
        kernel_stride = [1, 1, 1]
        kernel_dilation = [1, 1, 1]

        # size, in, out
        kernel = torch.rand(27, IC, OC).to(0)

        for batch_size in [2, 5, 10, 20, 40]:
            for voxel_size in [0.05, 0.035, 0.02]:
                min_time = 100000

                dcoords = torch.from_numpy(np.floor(coords / voxel_size)).int()
                bcoords = batched_coordinates([dcoords for i in range(batch_size)])

                tcolors = torch.from_numpy(colors).float()
                bcolors = torch.cat([tcolors for i in range(batch_size)]).to(0)

                for i in range(10):
                    manager = _C.CoordinateMapManager()

                    # batch insert
                    in_key, (unique_map, inverse_map) = manager.insert_and_map(
                        bcoords.to(0), [1, 1, 1], ""
                    )
                    ucolors = bcolors[unique_map.long()]
                    out_key = in_key

                    stime = time.time()
                    out_features = _C.ConvolutionForwardGPUf(
                        ucolors,
                        kernel,
                        kernel_size,
                        kernel_stride,
                        kernel_dilation,
                        _C.RegionType.HYPER_CUBE,
                        torch.IntTensor(),
                        in_key,
                        out_key,
                        manager,
                    )
                    min_time = min(time.time() - stime, min_time)

                print(f"{batch_size}\t{voxel_size}\t{manager.size(in_key)}\t{min_time}")