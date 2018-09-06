import argparse
import os
import random

import torch.backends.cudnn as cudnn
import torch.nn as nn
import torch.optim as optim
import torch.utils.data
import torchvision.transforms as transforms
from PIL import Image
from torch.autograd import Variable

import GAN.AI2018.DCGAN.DCGAN_model as model
# import custom package
import LJY_utils
import LJY_visualize_tools


# version conflict
import torch._utils
try:
    torch._utils._rebuild_tensor_v2
except AttributeError:
    def _rebuild_tensor_v2(storage, storage_offset, size, stride, requires_grad, backward_hooks):
        tensor = torch._utils._rebuild_tensor(storage, storage_offset, size, stride)
        tensor.requires_grad = requires_grad
        tensor._backward_hooks = backward_hooks
        return tensor
    torch._utils._rebuild_tensor_v2 = _rebuild_tensor_v2

#=======================================================================================================================
# Options
#=======================================================================================================================
parser = argparse.ArgumentParser()
# Options for path =====================================================================================================
parser.add_argument('--dataset', default='CelebA', help='what is dataset?')
parser.add_argument('--netG', default='/home/leejeyeol/Git/LJY_Machine_Learning/GAN/AI2018/DCGAN/output/netG_epoch_90.pth', help="path of Generator networks.(to continue training)")
parser.add_argument('--outf', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/DCGAN', help="folder to output images and model checkpoints")
#parser.add_argument('--outf', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/Test_Fake', help="folder to output images and model checkpoints")

parser.add_argument('--cuda', action='store_true', help='enables cuda')
parser.add_argument('--display', default=True, help='display options. default:False.')
parser.add_argument('--ngpu', type=int, default=1, help='number of GPUs to use')
parser.add_argument('--workers', type=int, default=1, help='number of data loading workers')
parser.add_argument('--iteration', type=int, default=50000, help='number of epochs to train for')

# these options are saved for testing
parser.add_argument('--batchSize', type=int, default=1, help='input batch size')
parser.add_argument('--imageSize', type=int, default=64, help='the height / width of the input image to network')
parser.add_argument('--model', type=str, default='pretrained_model', help='Model name')
parser.add_argument('--nc', type=int, default=3, help='number of input channel.')
parser.add_argument('--nz', type=int, default=100, help='dimension of noise.')
parser.add_argument('--ngf', type=int, default=64, help='number of generator filters.')
parser.add_argument('--ndf', type=int, default=64, help='number of discriminator filters.')

parser.add_argument('--seed', type=int, help='manual seed')

options = parser.parse_args()
print(options)



# save directory make   ================================================================================================
try:
    os.makedirs(options.outf)
except OSError:
    pass

# seed set  ============================================================================================================
if options.seed is None:
    options.seed = random.randint(1, 10000)
print("Random Seed: ", options.seed)
random.seed(options.seed)
torch.manual_seed(options.seed)

# cuda set  ============================================================================================================
if options.cuda:
    torch.cuda.manual_seed(options.seed)

torch.backends.cudnn.benchmark = True
cudnn.benchmark = True
if torch.cuda.is_available() and not options.cuda:
    print("WARNING: You have a CUDA device, so you should probably run with --cuda")


# ======================================================================================================================
# Data and Parameters
# ======================================================================================================================
display = options.display
dataset= options.dataset
batch_size = options.batchSize
ngpu = int(options.ngpu)
nz = int(options.nz)
ngf = int(options.ngf)
nc = int(options.nc)
# CelebA call and load   ===============================================================================================


makeimg= transforms.ToPILImage()
unorm = LJY_visualize_tools.UnNormalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))

# ======================================================================================================================
# Models
# ======================================================================================================================

# Generator ============================================================================================================
netG = model.Generator(ngpu, nz, ngf, nc)
netG.apply(LJY_utils.weights_init)
if options.netG != '':
    netG.load_state_dict(torch.load(options.netG))
print(netG)

# container generate
noise = torch.FloatTensor(batch_size, nz, 1, 1)

if options.cuda:
    netG.cuda()
    noise = noise.cuda()


# make to variables ====================================================================================================

noise = Variable(noise)

# for visualize
win_dict = LJY_visualize_tools.win_dict()

# training start
print("Training Start!")
for epoch in range(options.iteration):
    # generate noise    ============================================================================================
    noise.data.normal_(0, 1)
    # train with fake data   =======================================================================================
    fake = netG(noise)

    #visualize
    print('[%d/%d]' % (epoch, options.iteration))

    testImage = unorm(fake.data[0].cpu())
    makeimg(testImage).save(os.path.join(options.outf, '%05d.png' % epoch))

    if display:
        win_dict = LJY_visualize_tools.draw_images_to_windict(win_dict, [testImage], ["DCGAN_%s" % dataset])


# Je Yeol. Lee \[T]/