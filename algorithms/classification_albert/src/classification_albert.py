import Algorithmia

import time
import zipfile
from os import walk
import tensorflow as tf
from transformers import AlbertTokenizer, AlbertConfig
from transformers.modeling_tf_albert import TFAlbertForSequenceClassification
from transformers.data.processors.utils import InputFeatures


PAD_TOKEN = 0
NUM_LABELS = 2
DEFAULT_MAX_LEN = 128
DEFAULT_BATCH_SIZE = 16

MODEL_ZIP_PATH = "data://.my/classification_albert/model_params.zip"
UNZIPPED_MODEL_PATH = "model_params"


client = Algorithmia.client()


def get_unzipped_dir_path(zip_path_in_collection, dir_name):
    start = time.time()
    zip_in_collection = client.file(zip_path_in_collection).getFile().name
    output_dir = "/tmp/somedir"
    try:
        zipped_file = zipfile.ZipFile(zip_in_collection, "r")
        zipped_file.extractall(output_dir)
        zipped_file.close()
        duration = time.time() - start
        output_directory_name = None
        for dirpath, dirnames, filenames in walk(output_dir):
            for dirname in dirnames:
                output_directory_name = dirname
        print(f"Getting model data took {duration}")
    except Exception as e:
        print("Exception occurred while creating dir: {}".format(e))
    return "{}/{}".format(output_dir, output_directory_name)


def load_model_and_tokenizer():
    unzipped_saved_model_dir = get_unzipped_dir_path(
        MODEL_ZIP_PATH, UNZIPPED_MODEL_PATH
    )

    print("Loading pretrained ALBERT classification model")
    start = time.time()

    config = AlbertConfig.from_pretrained(unzipped_saved_model_dir, num_labels=NUM_LABELS, max_length=DEFAULT_MAX_LEN)
    model = TFAlbertForSequenceClassification.from_pretrained(unzipped_saved_model_dir, config=config)
    tokenizer = AlbertTokenizer.from_pretrained(unzipped_saved_model_dir, do_lower_case=True)

    duration = time.time() - start
    print(f"Initializing model took {duration}")
    
    return model, tokenizer


MODEL, TOKENIZER = load_model_and_tokenizer()


def _input_fn(texts, labels):
    features = []
    for text, label in zip(texts, labels):
        # docs are saying the add_prefix_space should be used
        inputs = TOKENIZER.encode_plus(
            text, None, add_special_tokens=True,
            max_length=DEFAULT_MAX_LEN,
            add_prefix_space=True)

        input_ids = inputs["input_ids"]
        attention_mask = [1] * len(input_ids)

        input_ids = _pad_with(input_ids, PAD_TOKEN, DEFAULT_MAX_LEN)
        attention_mask = _pad_with(attention_mask, PAD_TOKEN, DEFAULT_MAX_LEN)

        assert (len(input_ids) == DEFAULT_MAX_LEN)
        assert (len(attention_mask) == DEFAULT_MAX_LEN)

        features.append(InputFeatures(input_ids=input_ids,
                                      attention_mask=attention_mask,
                                      label=label))

    def gen():
        for f in features:
            yield ({'input_ids': f.input_ids,
                    'attention_mask': f.attention_mask
                    },
                   f.label)

    return tf.data.Dataset.from_generator(gen,
                                          ({'input_ids': tf.int32,
                                            'attention_mask': tf.int32},
                                           tf.float32),
                                          ({'input_ids': tf.TensorShape([None]),
                                            'attention_mask': tf.TensorShape([None])},
                                           tf.TensorShape([])))


def _pad_with(d, pad_token, desired_length):
    return d + [pad_token] * (desired_length - len(d))


def _predict_logits(texts):
    assert MODEL is not None
    start = time.time()
    labels = [0] * len(texts)
    test = _input_fn(texts, labels).batch(DEFAULT_BATCH_SIZE)
    print(f"Test data prep took {time.time() - start}")
    start = time.time()
    res = MODEL.predict(test)
    print(f"Prediction took {time.time() - start}")
    return res


def predict_proba(texts):
    weights = _predict_logits(texts)
    start = time.time()
    res = tf.nn.softmax(weights)[0][:,1].numpy()
    print(f"Result post-processing took {time.time() - start}")
    return res


def predict(texts, threshold=0.5):
    probabilities = predict_proba(texts)
    return (probabilities >= threshold).astype(int).tolist()

# API calls will begin at the apply() method, with the request body passed as 'input'
# For more details, see algorithmia.com/developers/algorithm-development/languages
def apply(input):
    texts = input["texts"]
    threshold = float(input.get("threshold", 0.5))
    print(f"Classifying {len(texts)} reviews with threshold {threshold}")
    return predict(texts, threshold)

if __name__=="__main__":
    print(apply({"texts": ["Hello", "Nice to meet you", "I can not login", "It does not work"]}))