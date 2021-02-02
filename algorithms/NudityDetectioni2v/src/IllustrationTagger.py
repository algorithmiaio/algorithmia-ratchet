import Algorithmia
# Ignore Python warnings because it makes the platform cry and complain
import warnings

warnings.filterwarnings("ignore")

import os
from caffe_i2v import make_i2v_with_caffe
import caffe
from PIL import Image
import json

# set to GPU mode
caffe.set_mode_gpu()


class AlgorithmError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class IllustrationTagger:
    def __init__(self, tags=None):
        # build the model here
        client = Algorithmia.client()
        
        self.model_loaded = False
        
        self.tag_list = "/tmp/tag_list"
        if os.path.isfile(self.tag_list):
            pass
        else:
            tmp_path = client.file("data://.my/nuditydetectioni2v/tag_list.json").getFile().name
            os.popen("mv " + tmp_path + " " + self.tag_list)

        if not isinstance(tags, type(None)):
            if len(self.getInvalidTagList(tags, self.tag_list)) != 0:
                raise AlgorithmError("Invalid tag. You can only provide a predefined tag.")

        self.prototxt = "/tmp/prototxt"
        if os.path.isfile(self.prototxt):
            pass
        else:
            tmp_path = client.file("data://.my/nuditydetectioni2v/illust2vec_tag.prototxt").getFile().name
            os.popen("mv " + tmp_path + " " + self.prototxt)

        self.caffemodel = "/tmp/caffemodel"
        if not os.path.isfile(self.caffemodel):
            tmp_path = client.file(
                "data://.my/nuditydetectioni2v/illust2vec_tag_ver200.caffemodel").getFile().name
            os.popen("mv " + tmp_path + " " + self.caffemodel)
        
        self.tags = tags
        
        self.init_model()
        
        self.model_loaded = True
        
        
    def init_model(self):
        self.model = make_i2v_with_caffe(self.prototxt, self.caffemodel, self.tag_list)
        self.model_loaded = True
    
    def unload_model(self):
        del self.model
        self.model_loaded = False
    
    def parseImage(self, urlData):
        client = Algorithmia.client()
        input_image = client.file(urlData).getFile().name
        return Image.open(input_image)

    def parseInput(self, input):
        rVal = {}

        if isinstance(input, basestring) or isinstance(input, bytearray):
            rVal["image"] = self.parseImage(input)
            rVal["threshold"] = 0.2
            rVal["tags"] = None
        elif isinstance(input, dict):
            if "image" not in input:
                raise AlgorithmError("Please provide image url or bytearray.")
            else:
                rVal["image"] = self.parseImage(input["image"])

            if "threshold" not in input:
                rVal["threshold"] = 0.2
            else:
                rVal["threshold"] = input["threshold"]

            if "tags" not in input:
                rVal["tags"] = None
            else:
                if not isinstance(input["tags"], list):
                    raise AlgorithmError("Please provide the tags in a list.")
                else:
                    rVal["tags"] = input["tags"]

            if "threshold" in input and "tags" in input:
                raise AlgorithmError("You cannot provide both the threshold and tags at the same time.")
        else:
            raise AlgorithmError("Please provide a valid input.")

        return rVal

    def getInvalidTagList(self, tagList, tagDictionaryPath):
        tagDictionary = json.loads(open(tagDictionaryPath, 'r').read())

        invalidTagList = []

        for tag in tagList:
            if tag not in tagDictionary:
                invalidTagList.append(tag)

        return invalidTagList

    def call(self, input):

        settings = self.parseInput(input)
        img = settings["image"]
        threshold = settings["threshold"]
        # tags = settings["tags"]
        tags = self.tags
        illust2vec = self.model

        if isinstance(img, list):
            rVal = []
            if isinstance(tags, type(None)):
                batch = illust2vec.estimate_plausible_tags(img, threshold=threshold)
                for img in batch:
                    tmp = {}
                    for i in img:
                        tmp[i] = []
                        for j in img[i]:
                            tmp[i].append({j[0]: j[1]})
                    rVal.append(tmp)
            else:
                batch = illust2vec.estimate_specific_tags(img, tags)
                for img in batch:
                    tmp = {}
                    tmp["all_tags"] = []
                    for i in img:
                            tmp["all_tags"].append({i: img[i]})
                    rVal.append(tmp)
        else:
            rVal = {}
            if isinstance(tags, type(None)):
                img = illust2vec.estimate_plausible_tags([img], threshold=threshold)[0]
                for i in img:
                    rVal[i] = []
                    for j in img[i]:
                        rVal[i].append({j[0]: j[1]})
            else:
                img = illust2vec.estimate_specific_tags([img], tags)[0]
                rVal["all_tags"] = []
                for i in img:
                    rVal["all_tags"].append({i: img[i]})
        print(str(rVal))
        return rVal