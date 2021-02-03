from .ops import *
from .utils import *
from glob import glob
import time
from tensorflow.contrib.data import prefetch_to_device, shuffle_and_repeat, map_and_batch
import numpy as np
import uuid

import Algorithmia
client = Algorithmia.client()

class UGATIT(object) :
    def __init__(self, sess):

        self.model_name = 'UGATIT'

        self.sess = sess

        self.batch_size = 1
        self.ch = 64

        self.smoothing = True

        self.n_res = 4

        self.img_size = 256
        self.img_ch = 3


    ##################################################################################
    # Generator
    ##################################################################################

    def generator(self, x_init, reuse=False, scope="generator"):
        channel = self.ch
        with tf.variable_scope(scope, reuse=reuse) :
            x = conv(x_init, channel, kernel=7, stride=1, pad=3, pad_type='reflect', scope='conv')
            x = instance_norm(x, scope='ins_norm')
            x = relu(x)

            # Down-Sampling
            for i in range(2) :
                x = conv(x, channel*2, kernel=3, stride=2, pad=1, pad_type='reflect', scope='conv_'+str(i))
                x = instance_norm(x, scope='ins_norm_'+str(i))
                x = relu(x)

                channel = channel * 2

            # Down-Sampling Bottleneck
            for i in range(self.n_res):
                x = resblock(x, channel, scope='resblock_' + str(i))


            # Class Activation Map
            cam_x = global_avg_pooling(x)
            cam_gap_logit, cam_x_weight = fully_connected_with_w(cam_x, scope='CAM_logit')
            x_gap = tf.multiply(x, cam_x_weight)

            cam_x = global_max_pooling(x)
            cam_gmp_logit, cam_x_weight = fully_connected_with_w(cam_x, reuse=True, scope='CAM_logit')
            x_gmp = tf.multiply(x, cam_x_weight)


            cam_logit = tf.concat([cam_gap_logit, cam_gmp_logit], axis=-1)
            x = tf.concat([x_gap, x_gmp], axis=-1)

            x = conv(x, channel, kernel=1, stride=1, scope='conv_1x1')
            x = relu(x)

            heatmap = tf.squeeze(tf.reduce_sum(x, axis=-1))

            # Gamma, Beta block
            gamma, beta = self.MLP(x, reuse=reuse)

            # Up-Sampling Bottleneck
            for i in range(self.n_res):
                x = adaptive_ins_layer_resblock(x, channel, gamma, beta, smoothing=self.smoothing, scope='adaptive_resblock' + str(i))

            # Up-Sampling
            for i in range(2) :
                x = up_sample(x, scale_factor=2)
                x = conv(x, channel//2, kernel=3, stride=1, pad=1, pad_type='reflect', scope='up_conv_'+str(i))
                x = layer_instance_norm(x, scope='layer_ins_norm_'+str(i))
                x = relu(x)

                channel = channel // 2


            x = conv(x, channels=3, kernel=7, stride=1, pad=3, pad_type='reflect', scope='G_logit')
            x = tanh(x)

            return x, cam_logit, heatmap

    def MLP(self, x, use_bias=True, reuse=False, scope='MLP'):
        channel = self.ch * self.n_res

        with tf.variable_scope(scope, reuse=reuse):
            for i in range(2) :
                x = fully_connected(x, channel, use_bias, scope='linear_' + str(i))
                x = relu(x)


            gamma = fully_connected(x, channel, use_bias, scope='gamma')
            beta = fully_connected(x, channel, use_bias, scope='beta')

            gamma = tf.reshape(gamma, shape=[self.batch_size, 1, 1, channel])
            beta = tf.reshape(beta, shape=[self.batch_size, 1, 1, channel])

            return gamma, beta


    ##################################################################################
    # Model
    ##################################################################################

    def generate_a2b(self, x_A, reuse=False):
        out, cam, _ = self.generator(x_A, reuse=reuse, scope="generator_B")

        return out, cam

    
    def build_model(self):

        """ Test """
        self.test_domain_A = tf.placeholder(tf.float32, [1, self.img_size, self.img_size, self.img_ch], name='test_domain_A')

        self.test_fake_B, _ = self.generate_a2b(self.test_domain_A)

    def save(self, checkpoint_dir, step):
        checkpoint_dir = os.path.join(checkpoint_dir, self.model_dir)

        if not os.path.exists(checkpoint_dir):
            os.makedirs(checkpoint_dir)

        self.saver.save(self.sess, os.path.join(checkpoint_dir, self.model_name + '.model'), global_step=step)

    def load(self, checkpoint_dir='/tmp/checkpoint/test.model'):



        from shutil import copyfile
        import os
        os.makedirs('/tmp/model', exist_ok=True)

        for file in client.dir('data://.my/selfie2anime/').files():
            print(file.path.split('/')[-1])
            src = client.file(file.path).getFile().name
            copyfile(src, '/tmp/model/'+file.path.split('/')[-1])

        print(" [*] Reading checkpoints...")
        checkpoint_dir='/tmp/model/test.model'

        self.saver = tf.train.Saver()
        self.saver.restore(self.sess, checkpoint_dir)

        print(" [*] Success to read {}".format(checkpoint_dir))
        return True


    def test(self, input, output):
        size=self.img_size
        import requests
        import numpy as np

        response = requests.get(input)
        resp = response.content
        img = np.frombuffer(resp, np.uint8)
        img = cv2.imdecode(img, cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        #crop
        h, w = img.shape[:2]

        if h>w:
            margin = int((h-w)/2)
            img = img[margin:h-margin,:]
        else:
            margin = int((w-h)/2)
            img = img[:,margin:w-margin]

        img = cv2.resize(img, dsize=(size, size))

        img = np.expand_dims(img, axis=0)
        sample_image = img/127.5 - 1


        print('Processing A image: ' + input)
        # sample_image = np.asarray(load_test_data(input, size=self.img_size))
        # image_path = os.path.join(output,'{0}'.format(os.path.basename(input)))
        image_path = output

        fake_img = self.sess.run(self.test_fake_B, feed_dict = {self.test_domain_A : sample_image})
        tempfile = "/tmp/"+str(uuid.uuid4())+".jpg"
        save_images(fake_img, [1, 1], tempfile)
        client.file(output).putFile(tempfile)

