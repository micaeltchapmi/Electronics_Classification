from pydicom import dcmread
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import cv2
import os
import platform
import albumentations as A
import random
from shared.data_utils import save_cdi_imgs, save_cdi_labels

# All x-rays should look like this, though perhaps flipped/rotated.You might expect a sideways x-ray but not an
# upside-down one.
# Images will have different brightnesses, contrasts, etc.

def train_val_test_split(data, data_labels, data_cache):
    _, full_labels = load_data_labels()   # full_labels includes image directory information | data labels is array of 6 output prediction coordinates
    
    n = len(data) # number of images total
    data_labels = data_labels[:n]

    trainInd, valInd, testInd = [], [], []

    trainingN, valN, testN = int(n * 0.6), int(n * 0.2), int(n * 0.2)

    random.seed(1) #initialize random seed to generate repeatable results
    processedSet = set()

    # debugging sets (can be removed)
    trainSet, valSet, testSet = set(), set(), set()

    for i in range(n):
        ranNum = random.random() # initialize random number
        imgID = full_labels.iloc[i]['lateral x-ray'][0:12] # unique image ID (i.e. JUPITERW001R)

        if imgID not in processedSet:
            processedSet.add(imgID)

            if ranNum < 0.34 and len(testInd) < testN: # add to test set
                testInd.append(i)
                testSet.add(imgID)
                
                for j in range(i + 1, n): # find all other images with same ID
                    nextImgID = full_labels.iloc[j]['lateral x-ray'][0:12]
                    if nextImgID == imgID:
                        testInd.append(j)
            elif ranNum < 0.68 and len(valInd) < valN: # add to val set
                valInd.append(i)
                valSet.add(imgID)
                
                for j in range(i + 1, n): # find all other images with same ID
                    nextImgID = full_labels.iloc[j]['lateral x-ray'][0:12]
                    if nextImgID == imgID:
                        valInd.append(j)
            else: # add to train set
                trainInd.append(i)
                trainSet.add(imgID)
                
                for j in range(i + 1, n): # find all other images with same ID
                    nextImgID = full_labels.iloc[j]['lateral x-ray'][0:12]
                    if nextImgID == imgID:
                        trainInd.append(j)

    train_img_name = [full_labels.iloc[i]['lateral x-ray'] for i in trainInd]
    val_img_name = [full_labels.iloc[i]['lateral x-ray'] for i in valInd]
    test_img_name = [full_labels.iloc[i]['lateral x-ray'] for i in testInd]

    trainData, train_data_labels, train_data_cache  = data[trainInd, :, :], data_labels[trainInd, :], (data_cache[:, trainInd], train_img_name)
    valData, val_data_labels, val_data_cache  = data[valInd, :, :], data_labels[valInd, :], (data_cache[:, valInd], val_img_name)
    testData, test_data_labels, test_data_cache  = data[testInd, :, :], data_labels[testInd, :], (data_cache[:, testInd], test_img_name)

    return trainData, train_data_labels, train_data_cache, valData, val_data_labels, val_data_cache, testData, test_data_labels, test_data_cache


def load_data(scale_dim=512, n=None, crop=True, subtract_mean=False):
    home_dir = os.getcwd()
    data_labels, full_labels = load_data_labels()   # full_labels includes image directory information
    data_labels = data_labels[:n]

    if n is None:
        n = len(data_labels)
    data = []
    for i in range(n):
        print("Processing image: ", i + 1, " / ", n)

        # load and store images in data array
        image_path = home_dir + '\\Images\\' + full_labels.iloc[i]['lateral x-ray']
        if platform.system() == 'Darwin':
            image_path = image_path.replace("\\", "/")
        ds = dcmread(image_path)
        image = ds.pixel_array  # pixel data is stored in 'pixel_array' element which is like a np array
        image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)  # normalize pixels range [0, 255]
        data.append(image)

    # store pixel dimension in cache for scaling back
    x_pix_dim = [len(image[0]) for image in data]
    y_pix_dim = [len(image) for image in data]
    data_cache = [x_pix_dim, y_pix_dim]

    # crop images
    if crop:
        data, data_labels = crop_images(data, data_labels)

    # scale images
    if scale_dim is not None:
        data, data_labels = rescale_images(data, data_labels, scale_dim)

    # subtract mean
    if subtract_mean:
        data = sub_mean(data)

    # convert to np array
    data = np.array(data)
    data_labels = np.array(data_labels)
    data_cache = np.array(data_cache)

    return data, data_labels, data_cache


def load_data_labels():
    home_dir = os.getcwd()
    # Read data labels Excel file, which includes image directory location and label (x, y) information
    label_dir = home_dir + '\\labels.xlsx'
    if platform.system() == 'Darwin':
        label_dir = label_dir.replace("\\", "/")
    # noinspection PyArgumentList
    full_labels = pd.read_excel(label_dir)
    data_labels = full_labels[['superior_patella_x', 'inferior_patella_x',
                          'tibial_plateau_x', 'superior_patella_y',
                          'inferior_patella_y', 'tibial_plateau_y']]
    data_labels = data_labels.to_numpy()
    return data_labels, full_labels


def crop_images(data, data_labels):
    cropped = []
    # crop image and labels into squares
    for i in range(len(data)):
        y_dim, x_dim = data[i].shape
        if y_dim > x_dim:
            start = (y_dim - x_dim) // 2
            end = (y_dim + x_dim) // 2
            im_cropped = data[i][start:end, :]

            data_labels[i][3:] -= start

        else:
            start = (x_dim - y_dim) // 2
            end = (x_dim + y_dim) // 2
            im_cropped = data[i][:, start:end]
            data_labels[i][:3] -= start
        cropped.append(im_cropped)
    return cropped, data_labels


def rescale_images(data, data_labels, scale_dim):
    scaled = []
    # scale labels
    for i in range(len(data)):
        scaled_im = cv2.resize(data[i], (scale_dim, scale_dim))
        y_pix_dim, x_pix_dim = data[i].shape
        data_labels[i][:3] *= scale_dim / x_pix_dim
        data_labels[i][3:] *= scale_dim / y_pix_dim
        scaled.append(scaled_im)
    return scaled, data_labels


def sub_mean(data, *argv):
    data = np.array(data).astype('float64')
    mean_im = np.mean(data, axis=0)
    std_im = np.std(data, axis=0)
    data = (data - mean_im) / std_im
    out = [data]
    for arg in argv:
        norm = (arg - mean_im) / std_im
        out.append(norm)
    out = tuple(out)
    return out


def show_image(image, label=None):
    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(111)
    plt.imshow(image, cmap='gray')

    if label is not None:
        plt.scatter(label[0], label[3])  # superior patella loc in blue
        plt.scatter(label[1], label[4])  # inferior patella loc in orange
        plt.scatter(label[2], label[5])  # tibial_plateau loc in green

    ax.set_xticks([])
    ax.set_yticks([])
    plt.show()


def augment(data, data_labels, data_cache, n=100):
    transform = A.Compose([
        A.RandomResizedCrop(width=data.shape[1], height=data.shape[2], scale=(0.8, 1.0), ratio=(0.75, 1.3333333333333333), p=0.7),
        A.RandomBrightnessContrast(p=0.9),
        A.Rotate(p=0.2),
        A.InvertImg(p=0.2),
        A.VerticalFlip(p=0.3),
        A.HorizontalFlip(p=0.3)
    ], keypoint_params=A.KeypointParams(format='xy'))

    idxs = np.random.randint(0, len(data), size=n)

    # reshape data_labels to tuples for transform operation
    keypoints = list(zip(zip(data_labels[:, 0], data_labels[:, 3]),
                         zip(data_labels[:, 1], data_labels[:, 4]),
                         zip(data_labels[:, 2], data_labels[:, 5])))
    trfm_images, trfm_keypoints, trfm_name = [],[],[]
    count = 0
    for i in idxs:
        transformed = transform(image=data[i], keypoints=keypoints[i])
        transformed_image = transformed['image']
        transformed_keypoints = transformed['keypoints']
        # reshape keypoint tuples back to original data_label shape
        transformed_keypoints = [transformed_keypoints[0][0], transformed_keypoints[1][0],
                                 transformed_keypoints[2][0], transformed_keypoints[0][1],
                                 transformed_keypoints[1][1], transformed_keypoints[2][1]]
        transformed_name = data_cache[i][:-4] + "_aug" + str((idxs[:count + 1] == i).sum()) + ".dcm"
        trfm_name.append(transformed_name)
        trfm_images.append(transformed_image)
        trfm_keypoints.append(transformed_keypoints)
        count += 1

    # convert to np array
    trfm_images = np.array(trfm_images)
    trfm_keypoints = np.array(trfm_keypoints)

    return trfm_images, trfm_keypoints, (idxs, trfm_name)


def unscale(image, label, data_cache):
    raise NotImplementedError




def main():
    # **********************************************************
    # load data (images and labels) and crop, rescale, and normalize (don't normalize yet if you want to augment data)
    data, data_labels, data_cache = load_data(scale_dim=128, n=None, crop=True, subtract_mean=False)
    print('Shape of original image array: ', data.shape)
    print('Shape of original labels array: ', data_labels.shape)

    trainData, train_data_labels, train_data_cache, valData, val_data_labels, val_data_cache \
        , testData, test_data_labels, test_data_cache = train_val_test_split(data, data_labels, data_cache)

    train_data_names = train_data_cache[1]
    test_data_names = test_data_cache[1]
    val_data_names = val_data_cache[1]

    # feed in originally loaded data into augment()
    # train_aug, train_aug_labels, train_aug_cache = augment(trainData, train_data_labels, train_data_cache[1], n=200)
    # combine original data and augmented data, and normalize
    # trainData = np.append(trainData, train_aug, axis=0)
    # train_data_labels = np.append(train_data_labels, train_aug_labels, axis=0)
    # train_data_names = train_data_cache[1] + train_aug_cache[1]

    trainData, valData, testData = sub_mean(trainData, valData, testData)

    dict = {}
    for i in range(len(train_data_names)):
        dict[train_data_names[i]] = train_data_labels[i]

    for i in range(len(test_data_names)):
        dict[test_data_names[i]] = test_data_labels[i]

    for i in range(len(val_data_names)):
        dict[val_data_names[i]] = val_data_labels[i]

    final_data = (trainData, train_data_labels, train_data_names,
                valData, val_data_labels, val_data_names,
                testData, test_data_labels, test_data_names)
    
    save_cdi_imgs(trainData, train_data_names, "train")
    save_cdi_imgs(valData, val_data_names, "val")
    save_cdi_imgs(testData, test_data_names, "test")

    save_cdi_labels(train_data_labels.tolist(), train_data_names)
    save_cdi_labels(val_data_labels.tolist(), val_data_names)
    save_cdi_labels(test_data_labels.tolist(), test_data_names)
    
    # print('Shape of final image array: ', trainData.shape)
    # print('Shape of final labels array: ', train_data_labels.shape)
    # print('Shape of final name array: ', len(train_data_names))
    # **********************************************************

if __name__=="__main__":
    main()


"""
# show all images in augmented data (first shows original, then augmented)
for i in range(len(cache)):
    show_image(data[cache[i]], data_labels[cache[i]])
    show_image(data_aug[i], data_aug_labels[i])

# show all images in data (does not include augmented data)
for i in range(len(data)):
    show_image(data[i], data_labels[i])

# show all images in data (does not include augmented data)
for i in range(len(data_final)):
    show_image(data_final[i], data_labels_final[i])

# show mean image
mean_im = np.mean(data, axis=0)
show_image(mean_im)
"""