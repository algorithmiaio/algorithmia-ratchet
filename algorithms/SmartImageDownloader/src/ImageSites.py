import Algorithmia
from Algorithmia.errors import AlgorithmException
from bs4 import BeautifulSoup
import requests
import re

class AlgorithmError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Imgur():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        s = BeautifulSoup(self.content)
        
        image_tags = s.find_all("div", "post-image")
        
        if len(image_tags) == 0:
            return []
        
        for image_tag in image_tags:
            # check of it's a gif or not
            # Currently only returns up to 10 images in galleries in Imgur
            # Uses javascript to get the rest of the images.
            # TODO: Get rest of the gallery images
            if "video" in str(image_tag):
                src_url = image_tag.find("meta", {"itemprop": "embedURL"})["content"]
                
                if src_url.startswith("//"):
                    src_url = "http:" + src_url
                
                rVal.append(src_url)
            else:
                src_url = image_tag.find("img")["src"]
                
                if src_url.startswith("//"):
                    src_url = "http:" + src_url
                
                rVal.append(src_url)
        
        return rVal

class Dropbox():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        s = BeautifulSoup(self.content)
        
        # If it's a single image
        if not isinstance(re.match("(http|https)://(www\.)?dropbox.com/s/.+", self.url), type(None)):
            base_url = "https://dl.getdropbox.com/s/"
            
            file_name = self.url.split("/")[-1]
            
            file_id = re.search("/s/(.+)?/", self.url).group(1)
            
            rVal.append(base_url + file_id + "/" + file_name)
        # If it's a dropbox album
        elif not isinstance(re.match("(http|https)://(www\.)?dropbox.com/sh/.+", self.url), type(None)):
            base_url = "https://dl.getdropbox.com/sh/"
            
            album_id = self.url.split("/")[4]
            
            file_names = re.findall("\"subPath\": \"(/.+?)\"", str(s))
            
            file_ids = re.findall("\"secureHash\": \"(.{25})\"}", str(s))
            
            if len(file_ids) != len(file_names):
                raise AlgorithmException("Parsing error. Please contact algorithm developer about issue.", "ParsingError")
            
            for i in range(len(file_names)):
                rVal.append(base_url + album_id + "/" + file_ids[i] + file_names[i])
                
        else:
            raise AlgorithmException("Dropbox link not supported. Please contact algorithm developer about issue.", "UnsupportedError")
        
        return rVal

class Wikipedia():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        # convert to PROPER wikimedia link
        self.url = "https://commons.wikimedia.org/wiki/File:" + "".join(self.url.split("File:")[1:])
        self.content = requests.get(self.url, "lxml").content
        
        s = BeautifulSoup(self.content)
        
        # Apparently there could be inconsistencies between wikipedia and wikipedia commons when it comes to files.
        # A file could be deleted due to copyright issues on the commons site, and still exist on the normal wikipedia site.
        
        try:
            img_link = s.find("a", "internal")["href"]
        except TypeError as e:
            # Let's see if the file has been deleted on wiki commons
            file_deleted = s.find("div", {"id": "mw-imagepage-nofile"})
            print file_deleted
            if len(file_deleted) >= 1:
                raise AlgorithmException("File has been deleted: For more information please refer to: " + self.url, "EntityNotFoundError")
            else:
                raise AlgorithmException("Cannot download wikipedia image. Please contact algorithm developer about issue.", "ParsingError")
        
        rVal.append(s.find("a", "internal")["href"])
        
        return rVal

class Twitter():
    # Twitter only allows up to 4 photos at once: https://support.twitter.com/articles/20156423
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        img_elments = s.find_all("div", "AdaptiveMedia-photoContainer")
        
        if len(img_elments) == 0:
            return rVal
            
        for img in img_elments:
            rVal.append(img.find("img")["src"])
        
        return rVal

class Flickr():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
        
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        # try scraping image links for none-gallery links
        rVal = self.__getImage()
        
        if len(rVal) == 0 and "galleries" in self.url.split("/"):
            # go to each page and do the normal operations
            base_url = "https://www.flickr.com"
            gallery_items = s.find("div", {"id": "gallery-big-photos"}).find_all("div", "gallery-item")
            
            for item in gallery_items:
                item_url = base_url + item.find("a", {"data-track": "photo-click"})["href"]
                rVal += self.__getImage(item_url)
        
        return rVal
    
    def __getImage(self, url=None):
        rVal = []
        
        flickr_formats = ["o", "l", "z", "m", "n", "k", "s", "t", "q", "sq"]
        
        if not isinstance(url, type(None)):
            content = requests.get(url, "lxml").content
        else:
            content = self.content
        
        for flickr_format in flickr_formats:
            img_links = re.findall("\"" + flickr_format + "\":{\"displayUrl\":\"(.+?)\",\"width\"", str(content))
            if len(img_links) != 0:
                break
        
        for img_link in img_links:
            img_link = img_link.replace("\\", "")
            
            if img_link.startswith("//"):
                img_link = "https:" + img_link
            
            rVal.append(img_link)
        
        return rVal

class Box():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        # check if it's a gallery
        gallery = s.find("div", "lia-media-list")
        
        if not isinstance(gallery, type(None)):
            base_url = "https://community.box.com"
            gallery_items = gallery.find_all("div", "lia-list-tile-image")
            
            for gallery_item in gallery_items:
                 item_url = base_url + gallery_item.find("a")["href"]
                 
                 rVal += self.__getImage(item_url)
        else:
            rVal = self.__getImage()
        
        return rVal
    
    def __getImage(self, url=None):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        if isinstance(url, type(None)):
            res = s.find("div", "lia-media-image-content-wrapper").find("img")["src"]
        else:
            content = requests.get(url, "lxml").content
            s = BeautifulSoup(content)
            
            res = s.find("div", "lia-media-image-content-wrapper").find("img")["src"]
            
        rVal.append("".join(res.split("/image-size/")[:1]))
        
        return rVal

class GooglePhotos():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        image_dimension_settings = "=w10000-h10000-no"
        
        s = BeautifulSoup(self.content)
        
        # Info about Google CDN: https://en.wiki-domains.net/wiki/googleusercontent.com
        image_hash_codes = re.findall(",\[\"(http|https)://(lh3|lh5|lh6).googleusercontent.com/(.+?)\",", str(s))
        image_url_links = map(lambda x: x[0] + "://" + x[1] + ".googleusercontent.com/" + x[2] + image_dimension_settings, image_hash_codes)
        print image_hash_codes
        # remove duplicate links
        rVal += list(set(image_url_links))
        
        return rVal

class GoogleDrive():
    def __init__(self, url):
        r = requests.get(url, "lxml")
        self.content = r.content
        self.redirectUrl = r.url
        self.url = url
        self.triedRedirect = False
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        folder_images = re.findall("\"https://(drive|docs).google.com/uc\?id\\\\u003d(.+?)\\\\u0026export\\\\u003ddownload\",", str(s))
        
        print len(folder_images)
        
        for image_hash in folder_images:
            rVal.append("https://docs.google.com/uc?id=" + image_hash[1] + "&export=download")
        
        # for redirecting Google Drive sharing links
        if len(rVal) == 0 and self.triedRedirect == False:
            self.triedRedirect = True
            self.url = self.redirectUrl
            self.content = requests.get(self.url, "lxml").content
            return self.getLinks()
        
        # get direct link(s) to Google Drive link(s)
        temp = []
        for gdrive_link in rVal:
            temp.append(requests.get(gdrive_link).url)
        
        rVal = temp
        
        return rVal
    
class Reddit():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        rVal += s.find("a", "title")["data-href-url"]
        
        return rVal

class Pinterest():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        rVal.append(s.find("div", "GrowthSEOPinImage").find("img")["src"])
        
        return rVal

class W500px():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        rVal.append(s.find("meta", {"property": "og:image"})["content"])
        
        return rVal

class Imageshack():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        base_url = "http://imageshack.com"
        
        link = base_url + s.find("img", {"id": "lp-image"})["src"]
        
        redirected_url = requests.get(link, "lxml").url
        
        rVal.append(redirected_url)
        
        return rVal

class W4chan():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
        
    def getLinks(self):
        rVal = []
        
        s = BeautifulSoup(self.content)
        
        link = s.find("div", "fileText").find("a")["href"]
        
        if link.startswith("//"):
            link = "http:" + link
        
        rVal.append(link)
        
        return rVal
        
class Instagram():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
    
    def getLinks(self):
        rVal = []
        
        r = re.findall('\"display_url\": \"(.+?)\"\,', self.content)
        
        if len(r) is 0:
            r = re.findall('property=\"og:image\" content=\"(.+?)\"', self.content)
        
        rVal += sorted(set(r), key=r.index)
        
        return rVal

class Facebook():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
        
    def getLinks(self):
        rVal = []
        
        return rVal

class VK():
    def __init__(self, url):
        self.content = requests.get(url, "lxml").content
        self.url = url
        
    def getLinks(self):
        rVal = []
        
        return rVal