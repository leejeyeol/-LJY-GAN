import argparse
import os
import random
import glob as glob
import torch.backends.cudnn as cudnn
import torch.nn as nn
import torch.utils.data
import torchvision.transforms as transforms
from torch.autograd import Variable
import torch.optim as optim
import GAN.AI2018.DCGAN.DCGAN_model as DCmodel
import GAN.AI2018.WGAN.WGAN_model as Wmodel
import GAN.AI2018.LSGAN.LSGAN_model as LSmodel
import GAN.AI2018.EBGAN.EBGAN_model as EBmodel
# import custom package
import LJY_utils
import LJY_visualize_tools
from PIL import Image

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


class Classifier(nn.Module):
    def __init__(self, ngpu, ndf = 64):
        super(Classifier, self).__init__()
        self.ngpu = ngpu
        self.feature_extract = nn.Sequential(
            nn.Conv2d(3, ndf, 4, 2, 1, bias=False),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf) x 32 x 32
            nn.Conv2d(ndf, ndf * 2, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 2),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*2) x 16 x 16
            nn.Conv2d(ndf * 2, ndf * 4, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 4),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*4) x 8 x 8
            nn.Conv2d(ndf * 4, ndf * 8, 4, 2, 1, bias=False),
            nn.BatchNorm2d(ndf * 8),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*8) x 4 x 4
            nn.Conv2d(ndf * 8, 96, 4, 1, 0, bias=False),
            nn.LeakyReLU(0.2, inplace=True)
        )
        self.fully_connected = nn.Sequential(

            nn.Linear(100, 100),
            nn.ReLU(True),

            nn.Linear(100, 100),
            nn.ReLU(True),

            nn.Linear(100, 100),
            nn.ReLU(True),

            nn.Linear(100, 1),
            nn.Sigmoid()
        )

    def forward(self, input, pretrained_D):
        if input.is_cuda and self.ngpu > 1:
            feature = nn.parallel.data_parallel(self.feature_extract, input, range(self.ngpu))
            output = nn.parallel.data_parallel(self.feature_extract, torch.cat((feature, pretrained_D), 1), range(self.ngpu))
        else:
            feature = self.feature_extract(input)
            output = self.fully_connected(torch.cat((feature.view(feature.shape[0], feature.shape[1]), pretrained_D), 1))
        return output


class Train_Dataloader(torch.utils.data.Dataset):
    def __init__(self, path_real,path_DC,path_W,path_LS,path_EB, transform):
        super().__init__()
        self.transform = transform

        assert os.path.exists(path_real)
        self.base_path_real = path_real

        assert os.path.exists(path_DC)
        self.base_path_DC = path_DC

        assert os.path.exists(path_W)
        self.base_path_W = path_W

        assert os.path.exists(path_LS)
        self.base_path_LS = path_LS

        assert os.path.exists(path_EB)
        self.base_path_EB = path_EB

        cur_file_paths = sorted(glob.glob(self.base_path_real + '/*.*'))
        # for random sample
        # random_files = random.sample(range(0, len(cur_file_paths)), options.num_fake_data * 4)
        # self.file_paths = [cur_file_paths[i] for i in random_files]
        self.file_paths = cur_file_paths[0:options.num_fake_data*4]
        self.label = [0 for _ in range(len(self.file_paths))]

        cur_file_paths = sorted(glob.glob(self.base_path_DC + '/*.*'))
        self.file_paths = self.file_paths + cur_file_paths
        self.label = self.label + [1 for _ in range(options.num_fake_data)]

        cur_file_paths = sorted(glob.glob(self.base_path_W + '/*.*'))
        self.file_paths = self.file_paths + cur_file_paths

        self.label = self.label + [1 for _ in range(options.num_fake_data)]

        cur_file_paths = sorted(glob.glob(self.base_path_LS + '/*.*'))
        self.file_paths = self.file_paths + cur_file_paths
        self.label = self.label + [1 for _ in range(options.num_fake_data)]

        cur_file_paths = sorted(glob.glob(self.base_path_EB + '/*.*'))
        self.file_paths = self.file_paths + cur_file_paths
        self.label = self.label + [1 for _ in range(options.num_fake_data)]

    def pil_loader(self,path):
        # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
        with open(path, 'rb') as f:
            with Image.open(f) as img:
                return img.convert('RGB')

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, item):
        path, label = self.file_paths[item], self.label[item]

        img = self.pil_loader(path)
        if self.transform is not None:
            img = self.transform(img)

        return img, label


class Eval_Dataloader(torch.utils.data.Dataset):
    def __init__(self, real_data_path, fake_data_path, transform):
        super().__init__()
        self.transform = transform
        assert os.path.exists(real_data_path)
        self.base_path_real = real_data_path
        cur_file_paths = sorted(glob.glob(self.base_path_real + '/*.*'))
        self.file_paths = cur_file_paths[options.num_fake_data*4:options.num_fake_data*4+2000]
        self.label = [0 for _ in range(len(self.file_paths))]

        assert os.path.exists(fake_data_path)
        self.base_path_fake = fake_data_path
        fake_file_paths = sorted(glob.glob(self.base_path_fake + '/*.*'))
        self.label= self.label + [int(os.path.basename(fake_file_paths[i]).split('.')[0].split('_')[-1]) for i in range(len(fake_file_paths))]
        self.file_paths = self.file_paths + fake_file_paths
        print(1)

    def pil_loader(self,path):
        # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
        with open(path, 'rb') as f:
            with Image.open(f) as img:
                return img.convert('RGB')

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, item):
        path, label = self.file_paths[item], self.label[item]

        img = self.pil_loader(path)
        if self.transform is not None:
            img = self.transform(img)

        return img, label


class Test_Dataloader(torch.utils.data.Dataset):
    def __init__(self, path, transform):
        super().__init__()
        self.transform = transform

        assert os.path.exists(path)
        self.base_path = path

        cur_file_paths = sorted(glob.glob(self.base_path + '/1_*.*'))
        self.file_paths = cur_file_paths

    def pil_loader(self,path):
        # open path as file to avoid ResourceWarning (https://github.com/python-pillow/Pillow/issues/835)
        with open(path, 'rb') as f:
            with Image.open(f) as img:
                return img.convert('RGB')

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, item):
        path = self.file_paths[item]

        img = self.pil_loader(path)


        if self.transform is not None:
            img = self.transform(img)

        return img

# ======================================================================================================================
# Options
# ======================================================================================================================
parser = argparse.ArgumentParser()
# Options for path =====================================================================================================
parser.add_argument('--dataset', default='CelebA', help='what is dataset?')
parser.add_argument('--dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/CelebA/Img/img_anlign_celeba_png.7z/img_align_celeba_png', help='path to dataset')
parser.add_argument('--Type', default='train', help='train, evaluation, test')

parser.add_argument('--DC_G_dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/DCGAN', help='path to dataset')
parser.add_argument('--W_G_dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/WGAN', help='path to dataset')
parser.add_argument('--LS_G_dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/LSGAN', help='path to dataset')
parser.add_argument('--EB_G_dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/EBGAN', help='path to dataset')
parser.add_argument('--eval_fake_dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_results/Test_Fake', help='path to dataset')
parser.add_argument('--test_dataroot', default='/media/leejeyeol/74B8D3C8B8D38750/Data/AI2018_FACE_test', help='path to dataset')

parser.add_argument('--net_DC_D', default='/home/leejeyeol/Git/LJY_Machine_Learning/GAN/AI2018/DCGAN/output/netD_epoch_90.pth', help="path of DCGAN Discriminator networks.(to continue training)")
parser.add_argument('--net_W_D', default='/home/leejeyeol/Git/LJY_Machine_Learning/GAN/AI2018/WGAN/output/netD_epoch_60.pth', help="path of WGAN Discriminator networks.(to continue training)")
parser.add_argument('--net_LS_D', default='/home/leejeyeol/Git/LJY_Machine_Learning/GAN/AI2018/LSGAN/output/netD_epoch_130.pth', help="path of LSGAN Discriminator networks.(to continue training)")
parser.add_argument('--net_EB_D', default='/home/leejeyeol/Git/LJY_Machine_Learning/GAN/AI2018/EBGAN/output/netD_epoch_4.pth', help="path of EBGAN Discriminator networks.(to continue training)")

#parser.add_argument('--classifier', default='./output/classifier_0.pth', help="real, fake classifier")
parser.add_argument('--classifier', default='', help="real, fake classifier")

parser.add_argument('--outf', default='./output', help="folder to output images and model checkpoints")

parser.add_argument('--cuda', action='store_true', help='enables cuda')
parser.add_argument('--display', default=True, help='display options. default:False.')
parser.add_argument('--ngpu', type=int, default=1, help='number of GPUs to use')
parser.add_argument('--workers', type=int, default=1, help='number of data loading workers')
parser.add_argument('--iteration', type=int, default=1, help='number of epochs to train for')
parser.add_argument('--num_fake_data', type=int, default=50000, help='number of fake data')


# these options are saved for testing
parser.add_argument('--batchSize', type=int, default=200, help='input batch size')
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
ndf = int(options.ndf)
nc = int(options.nc)

# CelebA call and load   ===============================================================================================
transform = transforms.Compose([
    transforms.CenterCrop(150),
    transforms.Scale(64),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])

makeimg= transforms.ToPILImage()
unorm = LJY_visualize_tools.UnNormalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))

train_dataloader = torch.utils.data.DataLoader(Train_Dataloader(options.dataroot, options.DC_G_dataroot,options.W_G_dataroot,
                                                    options.EB_G_dataroot,options.LS_G_dataroot, transform),
                                         batch_size=options.batchSize, shuffle=True, num_workers=options.workers)

eval_dataloader = torch.utils.data.DataLoader(Eval_Dataloader(options.dataroot, options.eval_fake_dataroot, transform),
                                         batch_size=1, shuffle=True, num_workers=options.workers)

transform_resize = transforms.Compose([
            transforms.Scale(64),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
        ])

test_dataloader = torch.utils.data.DataLoader(Test_Dataloader(options.test_dataroot, transform_resize),
                                         batch_size=1, shuffle=True, num_workers=options.workers)

MSE = nn.MSELoss()
BCE = nn.BCELoss()
# ======================================================================================================================
# Models
# ======================================================================================================================
# Discriminator ========================================================================================================
classifier = Classifier(ngpu, nz)
classifier.apply(LJY_utils.weights_init)
if options.classifier != '':
    classifier.load_state_dict(torch.load(options.classifier))
print(classifier)

# Discriminator ========================================================================================================
net_DC_D = DCmodel.Discriminator(ngpu, ndf, nc)
net_DC_D.apply(LJY_utils.weights_init)
if options.net_DC_D != '':
    net_DC_D.load_state_dict(torch.load(options.net_DC_D))
print(net_DC_D)

# Discriminator ========================================================================================================
net_W_D = Wmodel.Discriminator(ngpu, ndf, nc)
net_W_D.apply(LJY_utils.weights_init)
if options.net_W_D != '':
    net_DC_D.load_state_dict(torch.load(options.net_W_D))
print(net_W_D)

# Discriminator ========================================================================================================
net_LS_D = LSmodel.Discriminator(ngpu, ndf, nc)
net_LS_D.apply(LJY_utils.weights_init)
if options.net_LS_D != '':
    net_LS_D.load_state_dict(torch.load(options.net_LS_D))
print(net_LS_D)

# Discriminator ========================================================================================================
net_EB_D = EBmodel.Discriminator(ngpu, ndf, nc)
net_EB_D.apply(LJY_utils.weights_init)
if options.net_EB_D != '':
    net_EB_D.load_state_dict(torch.load(options.net_EB_D))
print(net_EB_D)

optimizer = optim.Adam(classifier.parameters(), betas=(0.5, 0.999), lr=2e-4)

if options.cuda:
    classifier = classifier.cuda()
    net_DC_D = net_DC_D.cuda()
    net_EB_D = net_EB_D.cuda()
    net_W_D = net_W_D.cuda()
    net_LS_D = net_LS_D.cuda()
    MSE = MSE.cuda()

if options.Type == 'train':
    print("Train")
    for epoch in range(options.iteration):
        for i, (data, label) in enumerate(train_dataloader, 0):
            classifier.zero_grad()

            input = Variable(data, volatile=True)
            if options.cuda:
                input = input.cuda()
            output_DC_DC = net_DC_D(input)
            output_W_DC = net_W_D(input)
            output_LS_DC = net_LS_D(input)
            output_EB_DC = net_EB_D(input)
            output_EB_DC = torch.mean(torch.mean(torch.mean((output_EB_DC - input)**2, 1), 1), 1)

            input = Variable(data, requires_grad=True)
            label = Variable(label, volatile=True)
            pretrained_D = Variable(torch.stack((output_DC_DC.data, output_W_DC.data, output_LS_DC.data, output_EB_DC.data), 1),
                     requires_grad=True)
            if options.cuda:
                input, label, pretrained_D = input.cuda(), label.cuda(), pretrained_D.cuda()

            output = classifier(input, pretrained_D)
            err = BCE(output, label.float().view(label.shape[0], 1))
            err.backward()
            optimizer.step()
            print('[%d/%d] err : %f' % (i, len(train_dataloader), err.data))

    torch.save(classifier.state_dict(), '%s/classifier_%d.pth' % (options.outf, epoch))

elif options.Type == 'evaluation':
    print("evaluate")
    # problem : it is generated fake data?
    TP = 0
    FP = 0
    FN = 0
    TN = 0
    for i, (data, label) in enumerate(eval_dataloader, 0):
        input = Variable(data, volatile=True)
        if options.cuda:
            input = input.cuda()
        output_DC_DC = net_DC_D(input)
        output_W_DC = net_W_D(input)
        output_LS_DC = net_LS_D(input)
        output_EB_DC = net_EB_D(input)
        output_EB_DC = torch.mean(torch.mean(torch.mean((output_EB_DC - input) ** 2, 1), 1), 1)

        input = Variable(data, volatile=True)
        label = Variable(label)
        pretrained_D = Variable(
            torch.stack((output_DC_DC.data, output_W_DC.data, output_LS_DC.data, output_EB_DC.data), 1))
        if options.cuda:
            input, label, pretrained_D = input.cuda(), label.cuda(), pretrained_D.cuda()
        label = label.float().view(label.shape[0], 1)

        output = classifier(input, pretrained_D)

        # Evaluation
        if (label.data[0] != 0).cpu().numpy():  # it's True
            if (output.data[0] >= 1 / 2).cpu().numpy():  # True
                TP += 1
            else:  # False
                FN += 1
        else:  # it's False label == 0
            if (output.data[0] <= 1 / 2).cpu().numpy():  # True
                TN += 1
            else:  # False
                FP += 1
        print('[%d/%d] output : %f, label : %f' % (i, 4000, output.data, label.data))
    print("TP : %d\t FN : %d\t FP : %d\t TN : %d\t" % (TP, FN, FP, TN))
    print("Accuracy : %f \t Precision : %f \t Recall : %f" % (
        (TP + TN) / (TP + TN + FP + FN), TP / (TP + FP), TP / (FN + TP)))

elif options.Type == 'test':
    print("test")
    for i, data in enumerate(test_dataloader, 0):
        input = Variable(data, volatile=True)
        if options.cuda:
            input = input.cuda()
        output_DC_DC = net_DC_D(input)
        output_W_DC = net_W_D(input)
        output_LS_DC = net_LS_D(input)
        output_EB_DC = net_EB_D(input)
        output_EB_DC = torch.mean(torch.mean(torch.mean((output_EB_DC - input) ** 2, 1), 1), 1)

        input = Variable(data, volatile=True)
        pretrained_D = Variable(
            torch.stack((output_DC_DC.data, output_W_DC.data, output_LS_DC.data, output_EB_DC.data), 1))
        if options.cuda:
            input, pretrained_D = input.cuda(), pretrained_D.cuda()

        output = classifier(input, pretrained_D)
        testImage = unorm(input.data.cpu().view(input.shape[1], input.shape[2], input.shape[3]))
        print(output.data[0].cpu().numpy())
        if (output.data[0] >= 1 / 2).cpu().numpy():  # True
            makeimg(testImage).save(os.path.join(options.outf, 'real_%5d.png') % i)
        else:  # False
            makeimg(testImage).save(os.path.join(options.outf, 'fake_%5d.png') % i)
# Je Yeol. Lee \[T]/