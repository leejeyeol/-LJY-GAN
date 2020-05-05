import numpy as np
import matplotlib.pyplot as plt
import re
import os
plt.style.use(['makina-notebook'])


def remove_char(line):
    return re.sub('\[|\]', '', line)


train_log_file = r'D:\experiments\HANON\log.txt'
show_action = True
action_list = ["rpm", "cooling_fan", "exv1", "exv2"]
def action_mapping(action_name, action):
    action = action + 1
    if action_name == "rpm":
        return action * 15  # * 8600
    elif action_name == "cooling_fan":
        return action * 10  # * 1500 + 1500
    else:
        return action * 5  # * 0.75 + 1.25


def moving_average(l, average_num = 10):
    result = [sum(l[i:i + average_num]) / average_num for i in range(len(l) - 10)]
    result = [0] * average_num + result
    return result


f = open(train_log_file, 'r')
lines = f.read().splitlines()
f.close()

train_lst = []
eval_lst = []
train_tem_list = []
eval_tem_list = []
episode_tem_list = []

w_list = lines[3].split(',')
num_of_info = len(lines[3].split(',')) - 5

info_meta_dict = {}
for i in range(1, num_of_info+1):
    info_dict = {}
    key = w_list[i + 3].split()[0]
    info_dict[key] = 0
    info_dict[key+'_train_mean'] = []
    info_dict[key+'_eval_mean'] = []
    info_meta_dict[key] = info_dict

reward = 0
train_reward_mean_list = []
eval_reward_mean_list = []

for l in lines:
    split_e = l.split()
    split_w = l.split(',')
    if l.startswith('Episode number'):
        if split_e[4] == 'Training':
            flag = 'train'
        else:
            flag = 'eval'
        target_tem = -1

    if l.startswith("Step number"):
        if target_tem == -1:
            target_tem = float(split_e[6]) - float(split_e[7])
        episode_tem_list.append([float(split_e[6])-target_tem, 0])

        if show_action is True:
            for i, action in enumerate(action_list):
                episode_tem_list[-1].append(action_mapping(action, float(remove_char(split_w[2]).split()[i+1])))

        for i in range(1, num_of_info+1):
            meta_key = split_w[i + 3].split()[0]
            info_dict = info_meta_dict[meta_key]
            if 'cop' in meta_key:
                info_dict[meta_key] += np.clip(float(split_w[i + 3].split()[2]), 0, 20)
            else:
                info_dict[meta_key] += float(split_w[i + 3].split()[2])

    if l.startswith('Episode score'):
        if flag == 'train':
            train_lst.append(float(split_e[2][:-1]))
            train_tem_list.append(episode_tem_list)
            episode_tem_list = []

            for meta_key in info_meta_dict.keys():
                info_dict = info_meta_dict[meta_key]
                info_dict[meta_key+'_train_mean'].append(info_dict[meta_key] / 20)
                info_dict[meta_key] = 0
        else:
            eval_lst.append(float(split_e[2][:-1]))
            eval_tem_list.append(episode_tem_list)
            episode_tem_list = []

            for meta_key in info_meta_dict.keys():
                info_dict = info_meta_dict[meta_key]
                info_dict[meta_key+'_eval_mean'].append(info_dict[meta_key] / 20)
                info_dict[meta_key] = 0

for i in range(1, num_of_info + 1):
    meta_key = w_list[i + 3].split()[0]
    info_dict = info_meta_dict[meta_key]
    info_dict[meta_key + '_train_average_move'] = moving_average(info_dict[meta_key + '_train_mean'])

    info_dict[meta_key + '_eval_average_move'] = moving_average(info_dict[meta_key + '_eval_mean'])


train_move = moving_average(train_lst)
eval_move = moving_average(eval_lst)


train_iter = len(train_tem_list)
for epi in range(train_iter):

    fig, ax = plt.subplots(1, 2+num_of_info, figsize=(10+5*num_of_info, 5))
    ax[0].plot(np.asarray(train_tem_list)[epi], marker='o', alpha=0.7, markersize=5)
    ax[0].set_title('Episode : %d' % (epi + 1))
    ax[0].set_ylim(-20, 50)
    ax[0].set_xlim(0, 20)
    ax[0].set_xticks(np.arange(0, 20, step=5))
    ax[0].set_xlabel('Step')
    ax[0].set_ylabel('Temperature')
    legend = ['Temperature', 'Zero']
    if show_action:
        legend = legend + action_list
    ax[0].legend(legend)

    ax[1].plot(np.asarray(train_move)[:epi], marker='o', alpha=0.7, markersize=2)
    ax[1].set_ylim(-20, 120)
    ax[1].set_xlim(0, train_iter)
    ax[1].set_xlabel('Episode')
    ax[1].set_ylabel('Return')
    ax[1].legend(['Return'])

    for i, meta_key in enumerate(info_meta_dict.keys()):
        info_dict = info_meta_dict[meta_key]
        ax[i+2].plot(np.asarray(info_dict[meta_key+'_train_average_move'])[:epi], marker='o', alpha=0.7, markersize=2)
        #ax[i+2].set_ylim(-2.5, 2.5)
        ax[i+2].set_xlim(0, train_iter)
        ax[i+2].set_xlabel('Episode')
        #ax[i+2].set_ylabel(meta_key)
        ax[i+2].legend([meta_key])

    #plt.show()
    plt.savefig(r'D:\experiments\HANON\figure_animation\train\fig_%05d'%(epi))
    plt.close()
    print('[%d/%d]'%(epi, train_iter))

evel_iter = len(eval_tem_list)
for epi in range(evel_iter):
    fig, ax = plt.subplots(1, 2+num_of_info, figsize=(10+5*num_of_info, 5))

    ax[0].plot(np.asarray(eval_tem_list)[epi], marker='o', alpha=0.7, markersize=5)
    ax[0].set_title('Episode : %d' % (epi + 1))
    ax[0].set_ylim(-20, 50)
    ax[0].set_xlim(0, 20)
    ax[0].set_xticks(np.arange(0, 20, step=5))
    ax[0].set_xlabel('Step')
    ax[0].set_ylabel('Temperature')
    legend = ['Temperature', 'Zero']
    if show_action:
        legend = legend + action_list
    ax[0].legend(legend)

    ax[1].plot(np.asarray(eval_move)[:epi], marker='o', alpha=0.7, markersize=2)
    ax[1].set_ylim(-20, 120)
    ax[1].set_xlim(0, evel_iter)
    ax[1].set_xlabel('Episode')
    ax[1].set_ylabel('Return')
    ax[1].legend(['Return'])

    for i, meta_key in enumerate(info_meta_dict.keys()):
        info_dict = info_meta_dict[meta_key]
        ax[i+2].plot(np.asarray(info_dict[meta_key+'_eval_average_move'])[:epi], marker='o', alpha=0.7, markersize=2)
        #ax[i+2].set_ylim(0, 2.5)
        ax[i+2].set_xlim(0, train_iter)
        ax[i+2].set_xlabel('Episode')
        #ax[i+2].set_ylabel(meta_key)
        ax[i+2].legend([meta_key])

    #plt.show()
    plt.savefig(r'D:\experiments\HANON\figure_animation\eval\fig_%05d'%(epi))
    plt.close()
    print('[%d/%d]'%(epi, evel_iter))


os.system(r'ffmpeg -r 32  -i D:\experiments\HANON\figure_animation\train\fig_%05d.png  -vf scale="480:480"  -filter:v "setpts=PTS"  -vcodec libx264 -pix_fmt yuv420p -acodec libvo_aacenc -ab 128k -y D:\experiments\HANON\figure_animation\train_x2.mov')
#os.system(r'ffmpeg -r 8  -i D:\experiments\HANON\figure_animation\train\fig_%05d.png  -vf scale="480:480"  -filter:v "setpts=PTS"  -vcodec libx264 -pix_fmt yuv420p -acodec libvo_aacenc -ab 128k -y D:\experiments\HANON\figure_animation\train.mov')
os.system(r'ffmpeg -r 8  -i D:\experiments\HANON\figure_animation\eval\fig_%05d.png  -vf scale="480:480"  -filter:v "setpts=PTS"  -vcodec libx264 -pix_fmt yuv420p -acodec libvo_aacenc -ab 128k -y D:\experiments\HANON\figure_animation\eval.mov')

