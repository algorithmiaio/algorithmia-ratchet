import Algorithmia
from Algorithmia.errors import AlgorithmException
import re
import os
import subprocess
import requests
from requests.exceptions import ConnectionError
import uuid
import src.custom_imghdr as imghdr
import random
import urllib
import base64
from PIL import Image, ExifTags
from PIL import ImageFile
import magic
# Also process partial images (http://stackoverflow.com/a/23575424/1555313)
ImageFile.LOAD_TRUNCATED_IMAGES = True
from src.ImageSites import *
# make sure to use utf-8 everywhere
import sys

debug = True

supported_image_types = ["png", "bmp", "jpg", "jpeg", "tiff", "gif", "gifv", "webp"]

# these are all based on released chrome revisions
browser_headers = [
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743 Safari/537.36"},
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:44.0) Gecko/20100101 Firefox/44.0"}
]

defaultTargetDirectory = "data://.algo/<user>/smartimagedownloader/temp/"

class AlgorithmError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def apply(input):
    '''
    Note: Algorithm behaviour has an exception for dataAPI links with the disable_processing
        flag. Reasoning is that we have use-cases where we need to repsonse
        as soon as possible, and we're not interested in any of the
        meta-information (like original size) associated with the output.
        We will return None (null) for those fields respectively.
        For every other combination of inputs, the algorithm will behave the way
        it was intended.
    '''
    image = None
    rVal = {}
    height = None
    width = None
    max_dim = None
    img_format = None
    skip_process = False
    targetDirectory = defaultTargetDirectory

    if isinstance(input, str):
        image = input
    elif isinstance(input, dict):
        if "image" not in input:
            raise AlgorithmException("Please provide a valid input.", "InputError")
        else:
            if "disable_processing" in input:
                if input["disable_processing"] == True:
                    skip_process = True
            if "format" in input:
                img_format = input["format"]
            if "resize" not in input:
                width = None
                height = None
                max_dim = None
            else:
                if isinstance(input["resize"], dict):
                    if "width" not in input["resize"] or "height" not in input["resize"]:
                        raise AlgorithmException("Width and height missing in resize option.", "InputError")
                    else:
                        width = input["resize"]["width"]
                        height = input["resize"]["height"]
                        max_dim = None
                elif isinstance(input["resize"], int):
                    width = None
                    height = None
                    max_dim = input["resize"]
                else:
                    raise AlgorithmException("Please provide a valid input for resize option.", "InputError")
            if "targetDirectory" in input:
                targetDirectory = input["targetDirectory"]
            image = input["image"]
    elif isinstance(input, bytearray):
        image = input
    else:
        raise AlgorithmException("Please provide a valid input.", "InputError")
    
    # If dataAPI link is passed with no processing setting, just pass the link back.
    if skip_process == True and image.startswith("data://"):
        print "Skipping processing..."
        rVal = {}
        rVal["savePath"] = []
        rVal["originalDimensions"] = []
        rVal["savePath"].append(image)
        rVal["originalDimensions"].append({"height": None, "width": None})
        
        return rVal
    
    directLinks = getDirectLink(image)
    
    absPaths = map(lambda x: getAbsPath(x), directLinks)
    
    
    # TODO: do optional operations here
    
    # debugPrint("Height: " + str(height))
    # debugPrint("Width: " + str(width))
    # debugPrint("Max_dim: " + str(max_dim))
    
    # exif handling done here
    orientedPaths = map(lambda x: orientImage(x), absPaths)
    
    original_dimensions = map(lambda x: getImageDimensions(x), orientedPaths)
    resized_dimensions = None
    
    # Image resizing done here
    if not isinstance(height, type(None)) and not isinstance(width, type(None)):
        resizedPaths = map(lambda x: resizeImage(x, width, height), orientedPaths)
        debugPrint("Chosen " + str(width) + " x " + str(height) + " resizing.")
        resized_dimensions = map(lambda x: getImageDimensions(x), resizedPaths)
    elif not isinstance(max_dim, type(None)):
        resizedPaths = map(lambda x: resizeImage(x, max_dim), orientedPaths)
        debugPrint("Chosen max_dim: " + str(max_dim) + " resizing.")
        resized_dimensions = map(lambda x: getImageDimensions(x), resizedPaths)
    else:
        resizedPaths = absPaths
        debugPrint("No resizing selected.")
    
    # Image reformatting done here
    if not isinstance(img_format, type(None)):
        reformattedPaths = map(lambda x: reformatImage(x, img_format=img_format), resizedPaths)
    else:
        reformattedPaths = resizedPaths
        
    
    savePath = map(lambda x: saveFile(x, targetDirectory), reformattedPaths)
    
    rVal["savePath"] = savePath
    rVal["originalDimensions"] = original_dimensions
    if not isinstance(resized_dimensions, type(None)):
        rVal["resizedDimensions"] = resized_dimensions
    
    return rVal
        
def saveFile(absPath, targetDirectory):
    client = Algorithmia.client()
    
    # sometimes links may have encoded /'s in the filename, which causes the Data API to freakout
    # replace these /'s with _'s
    # eg: "http://i.amz.mshcdn.com/-7GkWZK3VrEKkXtNrca7705et1s=/fit-in/1440x1440/uploads%2F2016%2F7%2F22%2Fussbrooklyn_18.jpg"
    filename = absPath.split("/")[-1]
    proper_filename = urllib.unquote(filename).replace("/", "_")
    
    targetPath = targetDirectory + proper_filename
    
    debugPrint("targetPath: " + targetPath)
    
    client.file(targetPath).putFile(absPath)
    
    return targetPath

def getImageDimensions(img_abs_path):
    try:
        im = Image.open(img_abs_path)
    except IOError as e:
        raise AlgorithmException("Please provide a valid image/URL.", "InputError")
    
    return {"width": im.size[0], "height": im.size[1]}

def check_extensions(extension):
    global supported_image_types
    
    img_format = extension.replace(".", "")
    
    if img_format.lower() not in supported_image_types:
        raise AlgorithmException("Please provide a valid format: png, jpeg, bmp, gif, tiff or webp.", "UnsupportedError")

def reformatImage(img_abs_path, img_format=None, **kwargs):
    global supported_image_types

    try:
        im = Image.open(img_abs_path)
    except IOError as e:
        raise AlgorithmException("Please provide a valid image/URL.", "InputError")
        
    os.remove(img_abs_path)

    if not isinstance(img_format, type(None)):
        img_format = img_format.lower()
        
        # check it's a valid extension
        check_extensions(img_format)
        
        if img_format == "jpg":
            img_format = "jpeg"
        img_abs_path = img_abs_path.split(".")[0] + "." + img_format    
        
        # if im.mode != "RGB":
        im = im.convert("RGB")
        
        im.save(img_abs_path, img_format, **kwargs)
    else:
        img_format = im.format
        debugPrint("PIL detected img_format: " + img_format)
        
        img_format = img_format.lower()
        
        if not img_format in supported_image_types:
            raise AlgorithmException("Image format could not be detected.", "UnsupportedError")
        
        img_abs_path = img_abs_path + "." + img_format
        
        im.save(img_abs_path)
    
    return img_abs_path
    
def resizeImage(img_abs_path, arg1, arg2=None):
    try:
        im = Image.open(img_abs_path)
    except IOError as e:
        raise AlgorithmException("Please provide a valid image/URL.", "InputError")
    
    os.remove(img_abs_path)
    
    im_width, im_height = im.size
    if isinstance(arg2, type(None)):
        if im_width > im_height:
            ratio = im_height / float(im_width)
            im = im.resize((arg1, int(arg1 * ratio)), Image.ANTIALIAS)
        else:
            ratio = im_width / float(im_height)
            im = im.resize((int(arg1 * ratio), arg1), Image.ANTIALIAS)
    else:
        im = im.resize((arg1, arg2), Image.ANTIALIAS)
    
    im.save(img_abs_path)
    
    return img_abs_path

# if the image is a jpeg, re-orient the image based on the exif orientation tag
def orientImage(imagePath):
    try:
        image = Image.open(imagePath)
        os.remove(imagePath)
    except IOError as e:
        raise AlgorithmException("Please provide a valid image/URL.", "InputError")
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation' : break
        exif=dict(image._getexif().items())
        print "contains exif data"
        if exif[orientation] == 3:
            image = image.rotate(180, expand=True)
        elif exif[orientation] == 6:
            image = image.rotate(270, expand=True)
        elif exif[orientation] == 8:
            image = image.rotate(90, expand=True)
    except Exception, e:
        debugPrint("no exif data, failed to orient image")
        debugPrint(e)
    finally:
        if image.mode == "RGBA" or "transparency" in image.info:
            image = image.convert('RGBA')
        else:
            image = image.convert('RGB')
        image.save(imagePath)
        return imagePath

def debugPrint(message):
    if debug == True:
        print message
    else:
        pass

def getDirectLink(url):
    # Imgur
    if not isinstance(re.match("(http|https)://(www|m\.)?imgur.com/(gallery/)?.+", url), type(None)):
        debugPrint("Imgur selected.")
        return Imgur(url).getLinks()
    # Dropbox
    elif not isinstance(re.match("(http|https)://(www\.)?dropbox.com/(s|sh)/.+", url), type(None)):
        debugPrint("Dropbox selected.")
        return Dropbox(url).getLinks()
    # TODO: Facebook (too complicated)
    elif not isinstance(re.match("(http|https)://(www\.)?facebook.com/photo.php.+", url), type(None)):
        # return Facebook(url).getLinks()
        raise AlgorithmException("Facebook links aren't supported. Please try again with a different link/website.", "UnsupportedError")
    # Twitter
    elif not isinstance(re.match("(http|https)://(www\.)?twitter.com/(\w+)?/status/.+", url), type(None)):
        debugPrint("Twitter selected.")
        return Twitter(url).getLinks()
    # Flickr
    elif not isinstance(re.match("(http|https)://(www\.)?flickr.com/(photos|gp)/(\w+)?(galleries|albums)?.+", url), type(None)):
        debugPrint("Flickr selected.")
        return Flickr(url).getLinks()
    # Box
    elif not isinstance(re.match("(http|https)://community.box.com/t5/media/(\w+)?(gallerypage/\.)?.+", url), type(None)):
        debugPrint("Box selected.")
        return Box(url).getLinks()
    # Picasa: Is getting retired, focus on Google Photos
    # Google Photos
    elif not isinstance(re.match("(http|https)://photos.google.com/share/.+", url), type(None)) or not isinstance(re.match("(http|https)://goo.gl/photos/.+", url), type(None)):
        debugPrint("Google Photos selected.")
        return GooglePhotos(url).getLinks()
    # Google Drive
    elif not isinstance(re.match("(http|https)://drive.google.com/(open\?id\=|folderview\?id\=|file/d/).+", url), type(None)):
        debugPrint("Google Drive selected.")
        return GoogleDrive(url).getLinks()
    # TODO: Reddit (blocks bots)
    elif not isinstance(re.match("(http|https)://(www\.)?reddit.com/r/(\w+)?/comments/.+", url), type(None)):
        raise AlgorithmException("Reddit links aren't supported. Please try again with a different link/website.", "UnsupportedError")
    #    return Reddit(url).getLinks()
    # Pinterest
    elif not isinstance(re.match("(http|https)://(www\.)?pinterest.com/pin/.+", url), type(None)):
        debugPrint("Pinterest selected.")
        return Pinterest(url).getLinks()
    # 500px
    elif not isinstance(re.match("(http|https)://(marketplace\.|www\.)?500px.com/(photo|photos)/(\w+)?/.+", url), type(None)):
        debugPrint("500px selected.")
        return W500px(url).getLinks()
    # Wikipedia
    elif not isinstance(re.match("(http|https)://(\w{2,3}\.|commons\.)?(wikipedia|wikimedia).org/wiki/(\w+)?(\#/media/)?(File|Category):.+", url), type(None)):
        debugPrint("Wikipedia selected.")
        return Wikipedia(url).getLinks()
    # Imageshack
    elif not isinstance(re.match("(http|https)://(www\.)?imageshack.com/i/.+", url), type(None)):
        debugPrint("Imageshack selected.")
        return Imageshack(url).getLinks()
    # 4chan
    elif not isinstance(re.match("(http|https)://boards.4chan.org/[a-zA-Z0-9]{1,3}/thread/.+", url), type(None)):
        debugPrint("4chan selected.")
        return W4chan(url).getLinks()
    # TODO: Instagram (too complicated)
    elif not isinstance(re.match("(http|https)://(www\.)instagram.com/p/.+", url), type(None)):
        return Instagram(url).getLinks()
    #    return Instagram(url).getLinks()
    # TODO: ADD VK (Russian Facebook)
    # Give proper error message for file:/// type of URLs
    elif url.startswith("file://"):
        raise AlgorithmException("Local file URLs (file://) are not supported.", "UnsupportedError")
    # All other http(s) or data API links
    elif not isinstance(re.match("[\\w\\+]+://.+", url), type(None)):
        debugPrint("Data API/http(s) selected.")
        return [url]
    else:
        debugPrint("None selected. (probably bytearray or something)")
        return [url]

def getRandomHeader():
    return random.choice(browser_headers)

def fix_extension(extension, img_abs_path):
    # Tries to fix extension on best effort basis
    global supported_image_types
    new_img_abs_path = img_abs_path
    new_extension = extension
    
    # remove dot from extension
    if new_extension.startswith("."):
        new_extension = new_extension.replace(".", "")
    
    # remove query parameters from url/extension
    if "&" in new_extension:
        new_extension = new_extension.split("&")[0]
    
    # remove tilde from url/extension
    if "~" in new_extension:
        new_extension = new_extension.split("~")[0]
    
    debugPrint("img_size (in bytes): " + str(os.path.getsize(img_abs_path)))
    
    # if we don't get extension in the filename, check the header
    if len(new_extension) == 0 or not new_extension in supported_image_types:
        # First try with imghdr to determine image extension
        try:
            new_extension = imghdr.what(img_abs_path).lower()
        except Exception as e:
            new_extension = None
        
        # If extension is still not detected, use python-magic to detect
        try:
            if isinstance(new_extension, type(None)):
                mime = magic.Magic(mime=True)
                new_extension =  mime.from_file(img_abs_path)
                new_extension = new_extension.split("/")[-1].lower()
        except Exception as e:
            new_extension = None
        
        
        # if we still can't get the extension, the image is most likely corrupted,
        # or it's a link to something completely else (eg. html page)
        if isinstance(new_extension, type(None)):
            raise AlgorithmException("Image/Url is invalid, or image type not supported.", "UnsupportedError")
    
    if new_extension != extension.split(".")[0]:
        new_img_abs_path = new_img_abs_path.split(".")[0] + "." + new_extension
        os.rename(img_abs_path, new_img_abs_path)
    
    new_extension = "." + new_extension
    
    return (new_extension, new_img_abs_path)

def getAbsPath(imageUrl):
    """
    Downloads image from any given source:
        http(s) URL
        data API URL
        base64 encoded string
        byte stream (aka bytearray in python)
    
    returns the abs path of the downloaded image
    """
    image_content = None
    img_abs_path = None
    img_size = None
    random_uuid = str(uuid.uuid4())
    filename, extension = getFileName(imageUrl)
    
    if len(extension) != 0:
        img_abs_path = "/tmp/" + random_uuid + "." + extension
    else:
        img_abs_path = "/tmp/" + random_uuid
    
    if imageUrl.startswith("http://") or imageUrl.startswith("https://"):
        try:
            response = requests.get(imageUrl, headers=getRandomHeader(), verify=False)
        except ConnectionError as e:
            raise AlgorithmException("Image could not be found at the given URL.", "EntityNotFoundError")
        except Exception as e:
            raise e
        image_content = response.content
        
        f = open(img_abs_path, "wb")
        f.write(image_content)
        f.close()
    elif not isinstance(re.match("[\\w\\+]+://.+", imageUrl), type(None)):
        client = Algorithmia.client()
        
        # Check if file exists in the dataAPI
        if not client.file(imageUrl).exists():
            raise AlgorithmException(imageUrl + " was not found.", "EntityNotFoundError")
        
        temp_path = client.file(imageUrl).getFile().name
        os.rename(temp_path, img_abs_path)
        
    elif imageUrl.startswith("data:image/"):
        for img_ext in supported_image_types:
            if imageUrl.startswith("data:image/" + img_ext):
                imageData = imageUrl.replace("data:image/" + img_ext + ";base64,", "")
                with open(img_abs_path, 'wb') as output:
                    output.write(base64.b64decode(imageData))
    else:
        raise AlgorithmException("Please provide a valid image input.", "InputError")
    
    img_size = os.path.getsize(img_abs_path)
    
    debugPrint("First attempt extension: " + extension)
    
    # try to fix broken extensions
    extension, img_abs_path = fix_extension(extension, img_abs_path)
    
    # check extension
    check_extensions(extension)
    
    # format checking
    if not validFormat(img_abs_path):
        debugPrint(img_abs_path)
        raise AlgorithmException("Please provide a valid image format, we accept the following formats: PNG, JPG, BMP, GIF and TIFF.", "UnsupportedError")
    
    debugPrint("img_abs_path: " + img_abs_path)
    debugPrint("original_extension: " + extension)
    debugPrint("file_name: " + filename)
    debugPrint("img_size: " + str(img_size))
    
    return img_abs_path

def validFormat(fileAbsPath):
    img_type = imghdr.what(fileAbsPath)
    
    # first do normal image file check
    if isinstance(img_type, type(None)):
        ext = fileAbsPath.split("/")[-1].split(".")[-1]
        
        # also check for the extension in file name
        if not ext in supported_image_types:
            return False
        else:
            return True
    
    for img_ext in supported_image_types:
        if img_type.lower() == img_ext.lower():
            return True
    
    return False

def getFileName(urlData):
    rVal = None
    if isinstance(urlData, basestring):
        if len(urlData) > 250:
            debugPrint("Direct link: " + urlData[:250])
        else:
            debugPrint("Direct link: " + urlData)
        # If it's http(s) or a data API url.
        if not isinstance(re.match("[\\w\\+]+://.+", urlData), type(None)):
            outName = urlData.split('/')[-1]
            filename, img_ext = os.path.splitext(outName.split("?")[0])
            rVal = [filename, img_ext]
            rVal[1].replace(".", "")
        # If it's encoded in base64
        elif urlData.startswith("data:image/"):
            for img_ext in supported_image_types:
                if urlData.startswith("data:image/" + img_ext):
                    rVal = ["base64", img_ext]
                    rVal[1].replace(".", "")
                    return rVal
            raise AlgorithmException("Please only provide a base64 encoded image in the following formats: png, jpg, jpeg, gif, tiff, bmp.", "UnsupportedError")
        else:
            raise AlgorithmException("Please provide a valid url.", "InputError")
        return rVal
    elif isinstance(urlData, bytearray):
        # If it's a bytearray.
        extension = imghdr.what("", urlData)
        rVal = ["bytestream", extension]
        rVal[1].replace(".", "")
        return rVal
    else:
        raise AlgorithmException("Please provide a proper input.", "InputError")
