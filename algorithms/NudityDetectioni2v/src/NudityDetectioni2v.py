import Algorithmia
import time
from urllib2 import HTTPError
from IllustrationTagger import IllustrationTagger


class AlgorithmError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


# weights
wt_illus2vec = 0.88
wt_isitnude = 1 - wt_illus2vec
# ratings tags
i2vExplicitWt = 1
i2vQuestionableWt = 0.1
i2vSafeWt = -1
# sensitve tags
i2vNudeWt = 1.5
i2vPussyWt = 0.9
i2vAssWt = 0.7
i2vPenisWt = 0.9
i2vBreastsWt = 0.4
i2vNipplesWt = 0.8
i2vPufNipsWt = 0.5
# insensitive tags
i2vNoHumWt = -1

# error 429 stuff
numTries = 0
maxTries = 5

tags = ["explicit", "questionable", "safe", "nude", "pussy", "breasts", "penis", "nipples", "puffy nipples", "no humans"]
    
imageDownloader = Algorithmia.client().algo('<user>/SmartImageDownloader/latestPrivate')

def initModel(tags):
    return IllustrationTagger(tags)

ITag = initModel(tags)

def apply(input):
    
    rVal = None
    
    global ITag
    
    if ITag.model_loaded == False:
        ITag.init_model()
    
    if isinstance(input, basestring):
        if input == None or input == "":
            raise AlgorithmError("image cannot be null.")
        try:
            input = getImage(input)
        except:
            raise AlgorithmError("Invalid or inaccessible URL.")
        rVal = getComposite(input)
        
    elif isinstance(input, bytearray):
        rVal = getComposite(input)
        
    elif isinstance(input, dict):
        if "image" not in input:
            raise AlgorithmError("Please provide an image.")
        else:
            try:
                input["image"] = getImage(input["image"])
            except:
                raise AlgorithmError("Invalid or inaccessible URL.")
            rVal = getComposite(input["image"])
    elif isinstance(input, list):
        print(len(input))
        rVal = getComposite(input)
    # ITag.unload_model()
    return rVal

def getImage(image):
    ilow = image.lower()
    if ilow.startswith("http://") or ilow.startswith("https://"):
        return imageDownloader.pipe({"image":image, "resize": { "width": 224, "height": 224 }}).result['savePath'][0]
    else:
        return image

def getTag(selectedTag, tagList):
    for tagObject in tagList:
        if selectedTag in tagObject:
            return tagObject[selectedTag]
    raise AlgorithmError("Invalid tag requested.")


def parseComposite(i2vComposite, input):
    if isinstance(input, bytearray):
        input = None

    if i2vComposite > 0:
        return {"url": input, "confidence": i2vComposite, "nude": True}
    else:
        return {"url": input, "confidence": -i2vComposite, "nude": False}
    
def getComposite(input):
    # tags = ["explicit", "questionable", "safe", "nude", "pussy", "breasts", "penis", "nipples", "puffy nipples",
    #         "no humans"]
    # ITag = IllustrationTagger()
    global ITag

    # Retry with if we get HTTP error code 429
    try:
        # tagVal = ITag.call({"image": input, "tags": tags})
        tagVal = ITag.call(input)
    except HTTPError, e:
        global numTries
        global maxTries
        if numTries == maxTries:
            raise AlgorithmError("Tried to fetch the image 5 times but failed.")
        if e.code == 429:
            # try using exponential backoff, not linear tries
            # sleep 1, 2, 4, 8, 16... seconds
            time.sleep(1 << numTries)
            numTries += 1

            return getComposite(input)
        raise AlgorithmError("Image could not be fetched. Please provide a valid URL. " + "(Code: " + str(e.code) + ")")

    if isinstance(tagVal, list):
        rVal = []
        for img, i in zip(tagVal, range(0, len(tagVal))):
            allTags = img['all_tags']
            i2vExplicitVal = getTag("explicit", allTags)
            i2vQuestionableVal = getTag("questionable", allTags)
            i2vSafeVal = getTag("safe", allTags)
            # important ags that may supercede ratings tags
            i2vNudeVal = getTag("nude", allTags)
            i2vPussyVal = getTag("pussy", allTags)
            i2vBreastsVal = getTag("breasts", allTags)
            i2vPenisVal = getTag("penis", allTags)
            i2vNipVal = getTag("nipples", allTags)
            i2vPufNipVal = getTag("puffy nipples", allTags)
            i2vNoHumVal = getTag("no humans", allTags)

            ratingsComposite = i2vExplicitWt * i2vExplicitVal + i2vQuestionableWt * i2vQuestionableVal + i2vSafeWt * i2vSafeVal

            nudeTags = i2vNudeWt * i2vNudeVal + i2vPenisWt * i2vPenisVal + i2vPussyWt * i2vPussyVal + i2vBreastsWt * i2vBreastsVal + i2vNipplesWt * i2vNipVal + i2vPufNipsWt * i2vPufNipVal
            notNudeTags = i2vNoHumWt * i2vNoHumVal
            
            print(str(ratingsComposite))
            if (i2vNudeVal >= 0.25 or i2vPenisVal >= 0.25 or i2vPussyVal >= 0.25):
                i2vComposite = 1
            else:
                i2vComposite = ratingsComposite + nudeTags + notNudeTags

            if (i2vComposite > 1):
                tmp = parseComposite(float(1), input[i])
            elif (i2vComposite < -1):
                tmp = parseComposite(float(-1), input[i])
            else:
                tmp = parseComposite(i2vComposite, input[i])
            rVal.append(tmp)
    else:
        allTags = tagVal['all_tags']
        i2vExplicitVal = getTag("explicit", allTags)
        i2vQuestionableVal = getTag("questionable", allTags)
        i2vSafeVal = getTag("safe", allTags)
        # important ags that may supercede ratings tags
        i2vNudeVal = getTag("nude", allTags)
        i2vPussyVal = getTag("pussy", allTags)
        i2vBreastsVal = getTag("breasts", allTags)
        i2vPenisVal = getTag("penis", allTags)
        i2vNipVal = getTag("nipples", allTags)
        i2vPufNipVal = getTag("puffy nipples", allTags)
        i2vNoHumVal = getTag("no humans", allTags)

        ratingsComposite = i2vExplicitWt * i2vExplicitVal + i2vQuestionableWt * i2vQuestionableVal + i2vSafeWt * i2vSafeVal

        nudeTags = i2vNudeWt * i2vNudeVal + i2vPenisWt * i2vPenisVal + i2vPussyWt * i2vPussyVal + i2vBreastsWt * i2vBreastsVal + i2vNipplesWt * i2vNipVal + i2vPufNipsWt * i2vPufNipVal
        notNudeTags = i2vNoHumWt * i2vNoHumVal
        print("ratings: " +str(ratingsComposite))
        print("nudity: "+str(nudeTags))
        print("notNude: " + str(notNudeTags))
        
        if (i2vNudeVal >= 0.25 or i2vPenisVal >= 0.25 or i2vPussyVal >= 0.25):
            i2vComposite = 1
        else:
            i2vComposite = ratingsComposite + nudeTags + notNudeTags

        if (i2vComposite > 1):
            rVal = parseComposite(float(1), input)
        elif (i2vComposite < -1):
            rVal = parseComposite(float(-1), input)
        else:
            rVal = parseComposite(i2vComposite, input)
    return rVal