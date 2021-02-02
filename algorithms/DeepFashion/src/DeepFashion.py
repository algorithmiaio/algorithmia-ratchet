import numpy as np
import tensorflow as tf
from PIL import Image
import Algorithmia
import os
from uuid import uuid4
import time
from src import label_map_util

# This is code for most tensorflow object detection algorithms
# In this example it's tuned specifically for our open local_image_input_paths data example.


valid_extensions = ["png", "jpg", "jpeg", "bmp", "gif", "tiff"]
client = Algorithmia.client()
TEMP_COLLECTION = 'data://.session'
# TEMP_COLLECTION = 'data://zeryx/testing'
BOUNDING_BOX_ALGO = '<user>/BoundingBoxOnImage/latestPrivate'
SIMD_ALGO = "<user>/SmartImageDownloader/latestPrivate"
SSD_MODEL_FILE = "data://<user>/deepfashion/ssd_v1.1.pb"
LABEL_FILE = "data://<user>/deepfashion/label_map.pbtxt"
NUM_CLASSES = 51
SSD_LOCAL = None
LABEL_LOCAL = None

TYPE = "small"


class AlgorithmError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def load_model(model_type):
    global SSD_LOCAL, LABEL_LOCAL
    t_0 = time.time()
    if model_type == "small":
        if not SSD_LOCAL:
            SSD_LOCAL = client.file(SSD_MODEL_FILE).getFile().name
        path_to_model = SSD_LOCAL
    else:
        raise AlgorithmError("model type not found.")
    if not LABEL_LOCAL:
        LABEL_LOCAL = client.file(LABEL_FILE).getFile().name
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(path_to_model, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')
    label_map = label_map_util.load_labelmap(LABEL_LOCAL)
    categories = label_map_util.convert_label_map_to_categories(
        label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)
    t_1 = time.time()
    print("loading took... {} sec".format(str(t_1 - t_0)))
    return detection_graph, category_index, model_type


def load_labels(label_path):
    label_map = label_map_util.load_labelmap(label_path)
    categories = label_map_util.convert_label_map_to_categories(
        label_map, max_num_classes=NUM_CLASSES, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)
    return category_index


def load_image_into_numpy_array(image):
    (im_width, im_height) = image.size
    return np.array(image.getdata()).reshape(
        (im_height, im_width, 3)).astype(np.uint8)


def get_image(url):
    t_0 = time.time()
    output_url = client.algo(SIMD_ALGO).pipe({'image': str(url)}).result['savePath'][0]
    temp_file = client.file(output_url).getFile().name
    local_file = "/tmp/{}.{}".format(str(uuid4()), output_url.split('.')[-1])
    os.rename(temp_file, local_file)
    t_1 = time.time()
    print("image downloading took... {} sec".format(str(t_1 - t_0)))
    return local_file


def get_images(urls):
    files = []
    for url in urls:
        files.append(get_image(url))
    return files


def generate_gpu_config(memory_fraction):
    config = tf.ConfigProto()
    # config.gpu_options.allow_growth = True
    config.gpu_options.per_process_gpu_memory_fraction = memory_fraction
    return config


# This function runs a forward pass operation over the frozen graph,
# and extracts the most likely bounding boxes and weights.
def infer(graph, images, category_index, min_score):
    output = []
    t_0 = time.time()
    images_np = []
    for image in images:
        img = Image.open(image)
        images_np.append(load_image_into_numpy_array(img))
    images_np = np.asarray(images_np)
    with graph.as_default():
        with tf.Session(graph=graph, config=generate_gpu_config(0.4)) as sess:
            batch_size, height, width, _ = images_np.shape
            image_tensor = graph.get_tensor_by_name('image_tensor:0')
            batch_boxes = graph.get_tensor_by_name('detection_boxes:0')
            batch_scores = graph.get_tensor_by_name('detection_scores:0')
            batch_classes = graph.get_tensor_by_name('detection_classes:0')
            num_detections = graph.get_tensor_by_name('num_detections:0')
            (batch_boxes, batch_scores, batch_classes, num_detections) = sess.run(
                [batch_boxes, batch_scores, batch_classes, num_detections],
                feed_dict={image_tensor: images_np})
            # batch_boxes = np.squeeze(batch_boxes)
            batch_classes = batch_classes.astype(np.int32)
            # batch_scores = np.squeeze(batch_scores)
    for i in range(len(batch_boxes)):
        per_image = []
        for j in range(len(batch_boxes[i])):
            confidence = float(batch_scores[i][j])
            if confidence >= min_score:
                ymin, xmin, ymax, xmax = tuple(batch_boxes[i][j].tolist())
                ymin = int(ymin * height)
                ymax = int(ymax * height)
                xmin = int(xmin * width)
                xmax = int(xmax * width)
                class_name = category_index[batch_classes[i][j]]['name']
                per_image.append(
                    {
                        'bounding_box': {
                            'y0': ymin,
                            'y1': ymax,
                            'x0': xmin,
                            'x1': xmax
                        },
                        'article_name': class_name,
                        'confidence': confidence
                    }
                )
        output.append(per_image)
    t_1 = time.time()
    print("inference took... {} sec".format(t_1 - t_0))
    return output


def draw_boxes_and_save(local_image_input_paths, output_paths, boxes_data):
    request = []
    t0 = time.time()
    remote_image_paths = ["{}/{}.{}".format(TEMP_COLLECTION, str(uuid4()), image.split('.')[-1]) for image in
                          local_image_input_paths]
    temp_output_paths = ["{}/{}.{}".format(TEMP_COLLECTION, str(uuid4()), output_path.split('.')[-1]) for output_path in
                         output_paths]
    for remote_image_path, temp_output_path, box_data, local_image_path in zip(remote_image_paths, temp_output_paths,
                                                                               boxes_data, local_image_input_paths):
        per_image = {}
        per_image['imageUrl'] = remote_image_path
        per_image['imageSaveUrl'] = temp_output_path
        per_image['style'] = 'basic'
        boxes = []
        for box in box_data:
            coords = box['bounding_box']
            coordinates = {'left': coords['x0'], 'right': coords['x1'],
                           'top': coords['y0'], 'bottom': coords['y1']}
            text_objects = [{'text': box['article_name'], 'position': 'top'},
                            {'text': 'score: {}%'.format(box['confidence']), 'position': 'bottom'}]
            boxes.append({'coordinates': coordinates, 'textObjects': text_objects})
        per_image['boundingBoxes'] = boxes
        client.file(remote_image_path).putFile(local_image_path)
        request.append(per_image)
    temp_images = client.algo(BOUNDING_BOX_ALGO).pipe(request).result['output']
    for temp_image, output_path in zip(temp_images, output_paths):
        local_image = client.file(temp_image).getFile().name
        client.file(output_path).putFile(local_image)
    t1 = time.time()
    print("drawing/saving boxes took ... {} sec".format(t1 - t0))
    return output_paths


def type_check(dic, id, type):
    if isinstance(dic[id], type):
        return dic[id]
    else:
        raise AlgorithmError("'{}' must be of {}".format(str(id), str(type)))


def apply(input):
    tags_only = None
    threshold = 0.5
    if isinstance(input, str):
        input_images = [get_image(input)]
        output_paths = ["data://.algo/<user>/deepFashion/temp/{}.png".format(str(uuid4())) for _ in
                        range(len(input_images))]
    elif isinstance(input, dict):
        if 'image' in input:
            input_images = get_images(type_check(input, 'image', list))
        else:
            raise Exception("AlgoError3000: 'image' missing from input")
        if 'output' in input:
            output_paths = type_check(input, 'output', list)
        else:
            output_paths = ["data://.algo/<user>/deepFashion/temp/{}.png".format(str(uuid4())) for _ in
                            range(len(input_images))]
        if 'tags_only' in input:
            tags_only = input['tags_only']
    else:
        raise AlgorithmError("AlgoError3000: Invalid input")
    output = []
    box_outputs = infer(GRAPH, input_images, CAT_INDEX, threshold)
    box_outputs = [sorted(box_output, key=lambda k: k['confidence']) for box_output in box_outputs]
    if tags_only:
        for box_output in box_outputs:
            output.append({'articles': box_output})
    else:
        output_paths_final = draw_boxes_and_save(input_images, output_paths, box_outputs)
        for output_path_final, box_output in zip(output_paths_final, box_outputs):
            output.append({'articles': box_output, 'output': [output_path_final]})
    return output


GRAPH, CAT_INDEX, TYPE = load_model(TYPE)
