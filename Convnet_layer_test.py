import torch
import torch.nn as nn
from torch.autograd import Variable

# test input

tranposed = True

if tranposed is False:
    batch_size = 1
    in_channel = 1
    width = 224
    length = 224
else:
    batch_size = 1
    in_channel =200
    width = 1
    length = 1

'''
out_channel = [128, 64,32,128]
kernel_size = [9,7, 5, 3]
stride = [4,2,2,2] #default 1
padding = [1,1,1,1] # default 0
layers = []
'''


if not tranposed:
    #encoder
    out_channel = [256, 256, 256, 256, 256, 256, 256]
    kernel_size = [3, 3, 3, 3, 3, 3, 2]
    stride = [2, 2, 2, 2, 2, 2, 2]  # default 1
    padding = [1, 1, 1, 1, 0, 0, 0]  # default 0
    layers = []
else:
    #decoder
    out_channel = [256,256,256,256]
    kernel_size = [3,3,3,2]
    stride = [2,2,2,2] #default 1
    padding = [0,0,0,1] # default 0
    layers = []

'''
out_channel = [16, 32,64,128,1]
kernel_size = [4,4, 4, 4,4]
stride = [2,2,2,2,1] #default 1
padding = [1,1,1,1,0] # default 0
layers = []
'''
test_input = Variable(torch.FloatTensor(batch_size,in_channel,width,length))
print("test input")
print(test_input.size())
size = test_input.size()
print("===============")

if tranposed == False:

    for i in range(len(out_channel)):
        layers.append(nn.Conv2d(in_channel, out_channel[i], kernel_size[i], stride[i], padding[i]))
        print("nn.Conv2d(%d, %d, %s, %d, %d),"%(in_channel,out_channel[i],kernel_size[i],stride[i],padding[i]))
        in_channel = out_channel[i]
    print("===============")

    for j in range(len(layers)):
        result = layers[j](test_input)
        print("# %d*%d*%d => %d*%d*%d" % (size[1], size[2], size[3], result.size()[1], result.size()[2], result.size()[3]))
        size = result.size()
        test_input = result


else:


    for i in range(len(out_channel)):

        layers.append(nn.ConvTranspose2d(in_channel, out_channel[i], kernel_size[i], stride[i], padding[i]))
        print("nn.ConvTranspose2d(%d, %d, %s, %d, %d),"%(in_channel,out_channel[i],kernel_size[i],stride[i],padding[i]))
        in_channel = out_channel[i]
    print("===============")

    for j in range(len(layers)):
        result = layers[j](test_input)
        print("# %d*%d*%d => %d*%d*%d" % (
        size[1], size[2], size[3], result.size()[1], result.size()[2], result.size()[3]))
        size = result.size()
        test_input = result

print("===============")