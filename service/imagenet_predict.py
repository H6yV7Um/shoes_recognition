# -*- coding: utf-8 -*-

import argparse
import logging
import tensorflow as tf
import numpy as np
import tensorflow.contrib.slim as slim
import os

from gevent import monkey
from gevent import wsgi
from io import BytesIO
from requests import get
from flask import Flask, request as req
from flask_cors import CORS
from json import dumps
from keras.preprocessing.image import load_img, img_to_array
from keras.applications.imagenet_utils import preprocess_input
from tensorflow.contrib.slim.nets import resnet_v1


app = Flask(__name__)
cors = CORS(app)
monkey.patch_all()
global sess
global logits
global inputs
imagenet_model_path = 'IMAGENET_MODEL_PATH'


logging.basicConfig(level=logging.DEBUG)
model_path = ''
if imagenet_model_path not in os.environ:
    logging.info('{} not in sys environ'.format(imagenet_model_path))
    exit(1)
else:
    model_path = os.environ[imagenet_model_path]
# logging.info('loading the model from {}'.format(args.model_path))
logging.info('loading the model from {}'.format(model_path))
inputs = tf.placeholder(tf.float32, shape=[None, 224, 224, 3])
inputs = tf.image.per_image_standardization(inputs)
with slim.arg_scope(resnet_v1.resnet_arg_scope()):
    logits, end_points = resnet_v1.resnet_v1_50(inputs, num_classes=1000)
saver = tf.train.Saver()
sess = tf.Session()
# restore
saver.restore(sess, model_path)


@app.route("/imagenet/predict/<x>", methods=["POST", "GET"])
def predict(x):
    success = False
    pred = "illegal api"
    if x == "url":
        success, pred = predict_from_url(req.data)
    elif x == "file":
        fp = BytesIO(req.data)
        success, pred = predict_from_file(fp)
        # pred = [int(p) for p in pred]
        pred = int(pred)
    if success:
        return dumps({"pred": pred})
    else:
        return dumps({"error": pred})


def predict_from_url(url):
    logging.debug("download image file from %s", url)
    try:
        res = get(url, stream=True)
        fp = BytesIO(res.content)
    except:
        return False, "fail to get image from url"
    return predict_from_file(fp)


def predict_from_file(fp):
    try:
        img = load_img(fp, target_size=(224, 224))
        arr = img_to_array(img)
    except:
        return False, "fail to load image from data"
    return predict_from_arr(arr)


def predict_from_arr(arr):
    if isinstance(arr, np.ndarray):
        if arr.shape == (224, 224, 3):
            x = np.expand_dims(arr, axis=0)
            # x = preprocess_input(x)
            pred_logits = sess.run(logits, feed_dict={inputs: x})
            y = np.argmax(pred_logits)
            return True, y
        else:
            return False, "expect an array with shape (224, 224, 3)"
    return False, "expect a numpy.ndarray"


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--bind-to", type=str, default="localhost")
    # parser.add_argument("--port", type=int, default=50001)
    # parser.add_argument("--model_path", type=str)
    # args = parser.parse_args()

    # logging.basicConfig(level=logging.DEBUG)
    #
    # logging.info('loading the model from {}'.format(args.model_path))
    # inputs = tf.placeholder(tf.float32, shape=[None, 224, 224, 3])
    # with slim.arg_scope(resnet_v1.resnet_arg_scope()):
    #     logits, end_points = resnet_v1.resnet_v1_50(inputs, num_classes=1000)
    # saver = tf.train.Saver()
    # sess = tf.Session()
    # # restore
    # saver.restore(sess, args.model_path)

    logging.info('starting the api')
    # app.run(host=args.bind_to, port=args.port)
    # server = wsgi.WSGIServer((args.bind_to, args.port), app)
    server = wsgi.WSGIServer(('localhost', 50001), app)
    server.serve_forever()
