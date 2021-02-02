import math

class DefaultStyle(object):
    def __init__(self, img_w, img_h):
        self.style_obj = {}
        
        self.img_w = img_w
        self.img_h = img_h
        
        self.style_obj["bb_color"] = (255, 255, 255)
        self.style_obj["rect_thickness"] = 2
        
        self.style_obj["bb_outer_color"] = (0, 0, 0)
        self.style_obj["rect_outer_thickness"] = 1
        
        self.style_obj["bb_inner_color"] = (0, 0, 0)
        self.style_obj["rect_inner_thickness"] = 1
        
        self.style_obj["top_font_size"] = 10
        self.style_obj["bottom_font_size"] = 10
        
        self.style_obj["top_font_offset"] = 2
        self.style_obj["bottom_font_offset"] = 2
        
        self.style_obj["top_font_background_color"] = (255, 255, 255)
        self.style_obj["bottom_font_background_color"] = (255, 255, 255)
        
        self.style_obj["top_font_background_outline_color"] = (0, 0, 0)
        self.style_obj["bottom_font_background_outline_color"] = (0, 0, 0)
        
        self.style_obj["top_font_background_outline_thickness"] = 1
        self.style_obj["bottom_font_background_outline_thickness"] = 1
        
        self.style_obj["top_font_true_offset"] = self.style_obj["top_font_size"] + self.style_obj["rect_outer_thickness"] + self.style_obj["rect_inner_thickness"] + self.style_obj["top_font_offset"] + self.style_obj["top_font_background_outline_thickness"]*2
        self.style_obj["bottom_font_true_offset"] = self.style_obj["rect_outer_thickness"] + self.style_obj["rect_inner_thickness"] + self.style_obj["bottom_font_offset"] + self.style_obj["bottom_font_background_outline_thickness"]*2
        
        self.style_obj["top_font_color"] = (0, 0, 0)
        self.style_obj["bottom_font_color"] = (0, 0, 0)
        
        # Use default font that comes with Ubuntu
        self.style_obj["top_font_name"] = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        self.style_obj["bottom_font_name"] = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
        
        # Re-assess settings according to image dimensions, scale up when needed...
        self.reassess()
    
    def reassess(self):
        max_length = max(self.img_w, self.img_h) * 1.0
        increment = 1200
        
        if max_length < increment:
            return
        else:
            ratio = int(math.ceil(max_length / increment))
            self.style_obj["rect_thickness"] = ratio*self.style_obj["rect_thickness"]
            self.style_obj["rect_outer_thickness"] = ratio
            self.style_obj["rect_inner_thickness"] = ratio
            self.style_obj["top_font_offset"] = ratio*self.style_obj["top_font_offset"]
            self.style_obj["bottom_font_offset"] = ratio*self.style_obj["bottom_font_offset"]
            self.style_obj["top_font_background_outline_thickness"] = ratio
            self.style_obj["bottom_font_background_outline_thickness"] = ratio
            self.style_obj["top_font_size"] = ratio*self.style_obj["top_font_size"]
            self.style_obj["bottom_font_size"] = ratio*self.style_obj["bottom_font_size"]
            self.style_obj["top_font_true_offset"] = self.style_obj["top_font_size"] + self.style_obj["rect_outer_thickness"] + self.style_obj["rect_inner_thickness"] + self.style_obj["top_font_offset"] + self.style_obj["top_font_background_outline_thickness"]*2
            self.style_obj["bottom_font_true_offset"] = self.style_obj["rect_outer_thickness"] + self.style_obj["rect_inner_thickness"] + self.style_obj["bottom_font_offset"] + self.style_obj["bottom_font_background_outline_thickness"]*2

class BasicStyle(DefaultStyle):
    def __init__(self, img_w, img_h):
        super(BasicStyle, self).__init__(img_w, img_h)
