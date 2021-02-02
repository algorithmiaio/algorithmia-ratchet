import Algorithmia
from PIL import Image, ImageDraw, ImageFont
import os
import uuid
from src import predefined_styles

client = Algorithmia.client()


class AlgorithmError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def verify_input(input):
    '''
    Description: Verifies input for errors and incomplete options, etc.
    '''

    if isinstance(input, dict):
        if "imageUrl" not in input:
            raise AlgorithmError("Please provide imageUrl.")
        if not isinstance(input["imageUrl"], str):
            raise AlgorithmError("imageUrl must be a string.")

        if "imageSaveUrl" not in input:
            raise AlgorithmError("Please provide imageSaveUrl.")
        if not isinstance(input["imageSaveUrl"], str):
            raise AlgorithmError("imageSaveUrl must be a string.")

        if "boundingBoxes" not in input:
            raise AlgorithmError("Please provide boundingBoxes.")
        if not isinstance(input["boundingBoxes"], list):
            raise AlgorithmError("boundingBoxes must be a JSON list.")
    elif isinstance(input, list):
        for data in input:
            verify_input(data)
    else:
        raise AlgorithmError("Please provide a valid JSON object as an input.")
    return input


def draw_bounding_boxes(style_obj, img_obj, faceCoords):
    '''
    Description: Draws all of the bounding boxes and texts on the image.
    '''
    draw = ImageDraw.Draw(img_obj)

    bb_color = style_obj["bb_color"]
    bb_inner_color = style_obj["bb_inner_color"]
    bb_outer_color = style_obj["bb_outer_color"]

    rect_thickness = style_obj["rect_thickness"]
    rect_inner_thickness = style_obj["rect_inner_thickness"]
    rect_outer_thickness = style_obj["rect_outer_thickness"]

    for faceCoord in faceCoords:
        left = faceCoord["coordinates"]["left"]
        top = faceCoord["coordinates"]["top"]
        right = faceCoord["coordinates"]["right"]
        bottom = faceCoord["coordinates"]["bottom"]
        for i in range(rect_thickness + rect_inner_thickness + rect_outer_thickness):
            if i < rect_inner_thickness:
                draw.rectangle([left - i, top - i, right + i, bottom + i], outline=bb_inner_color)
            elif i < rect_thickness + rect_inner_thickness:
                draw.rectangle([left - i, top - i, right + i, bottom + i], outline=bb_color)
            else:
                draw.rectangle([left - i, top - i, right + i, bottom + i], outline=bb_outer_color)

        if "textObjects" in faceCoord:
            # Draw texts that come with the bounding box
            for text_obj in faceCoord["textObjects"]:
                if text_obj["position"].lower() == "top":
                    # Get font object
                    font = ImageFont.truetype(style_obj["top_font_name"], style_obj["top_font_size"])
                    # Get text background dimensions
                    background_w, background_h = font.getsize(text_obj["text"])
                    # Get coords
                    x0 = left
                    x1 = x0 + background_w
                    y0 = top - style_obj["top_font_true_offset"]
                    y1 = y0 + background_h
                    # Draw background for text object beforehand
                    draw.rectangle([x0 - 1, y0 + 1, x1 + 1, y1 + 1], fill=style_obj["top_font_background_color"],
                                   outline=style_obj["top_font_background_outline_color"])
                    # Draw text on background
                    draw.text([x0, y0], text_obj["text"], fill=style_obj["top_font_color"], font=font)
                elif text_obj["position"].lower() == "bottom":
                    # Get font object
                    font = ImageFont.truetype(style_obj["bottom_font_name"], style_obj["top_font_size"])
                    # Get text background dimensions
                    background_w, background_h = font.getsize(text_obj["text"])
                    # Get coords
                    x0 = left
                    x1 = x0 + background_w
                    y0 = bottom + style_obj["bottom_font_true_offset"]
                    y1 = y0 + background_h
                    # Draw background for text object beforehand
                    draw.rectangle([x0 - 1, y0 + 1, x1 + 1, y1 + 1], fill=style_obj["bottom_font_background_color"],
                                   outline=style_obj["bottom_font_background_outline_color"])
                    # Draw text on background
                    draw.text([x0, y0], text_obj["text"], fill=style_obj["bottom_font_color"], font=font)

    del draw

    return img_obj


def get_img_url(img_url):
    res = client.algo("<user>/SmartImageDownloader/latestPrivate").pipe({"image": img_url}).result

    img_data_path = res["savePath"][0]

    img_w = res["originalDimensions"][0]["width"]
    img_h = res["originalDimensions"][0]["height"]

    img_abs_path = client.file(img_data_path).getFile().name

    img_obj = Image.open(img_abs_path)

    # Garbage collection
    os.remove(img_abs_path)

    return img_obj, img_w, img_h


def imb_obj_to_data_url(img_obj, data_url):
    unique_id = str(uuid.uuid4())
    extension = data_url.split(".")[-1]
    img_abs_path = "/tmp/" + unique_id + extension
    if (extension == "jpg"):
        extension = "jpeg"
    img_obj.save(img_abs_path, format=extension)

    # Before uploading the file, make sure the directory exists
    # But first, lets check if it's a .session path - James Aug 30, 2017
    if ".session" not in data_url:
        dataDir = "/".join(data_url.split("/")[0:4])

        if not client.dir(dataDir).exists():
            client.dir(dataDir).create()

    client.file(data_url).putFile(img_abs_path)

    os.remove(img_abs_path)

    return


def get_color(color_input):
    # TODO
    # Return 3 int tuple with RGB value for given color input.
    return tuple(color_input)


def get_style(verified_input, img_w, img_h):
    if not "style" in verified_input:
        style = predefined_styles.BasicStyle(img_w, img_h)
        return style.style_obj
    else:
        if isinstance(verified_input["style"], str):
            if verified_input["style"].lower() == "basic":
                style = predefined_styles.BasicStyle(img_w, img_h)
                return style.style_obj
            else:
                raise AlgorithmError("Given style name was not found in predefined style list.")
        elif isinstance(verified_input["style"], dict):
            style = predefined_styles.BasicStyle(img_w, img_h)
            if "rect_thickness" in verified_input["style"]:
                style.style_obj["rect_thickness"] = verified_input["style"]["rect_thickness"]
            if "rect_outer_thickness" in verified_input["style"]:
                style.style_obj["rect_outer_thickness"] = verified_input["style"]["rect_outer_thickness"]
            if "rect_inner_thickness" in verified_input["style"]:
                style.style_obj["rect_inner_thickness"] = verified_input["style"]["rect_inner_thickness"]
            if "top_font_size" in verified_input["style"]:
                style.style_obj["top_font_size"] = verified_input["style"]["top_font_size"]
            if "bottom_font_size" in verified_input["style"]:
                style.style_obj["bottom_font_size"] = verified_input["style"]["bottom_font_size"]
            if "top_font_offset" in verified_input["style"]:
                style.style_obj["top_font_offset"] = verified_input["style"]["top_font_offset"]
            if "bottom_font_offset" in verified_input["style"]:
                style.style_obj["bottom_font_offset"] = verified_input["style"]["bottom_font_offset"]
            if "top_font_background_outline_thickness" in verified_input["style"]:
                style.style_obj["top_font_background_outline_thickness"] = verified_input["style"][
                    "top_font_background_outline_thickness"]
            if "bottom_font_background_outline_thickness" in verified_input["style"]:
                style.style_obj["bottom_font_background_outline_thickness"] = verified_input["style"][
                    "bottom_font_background_outline_thickness"]
            if "bb_color" in verified_input["style"]:
                style.style_obj["bb_color"] = get_color(verified_input["style"]["bb_color"])
            if "bb_outer_color" in verified_input["style"]:
                style.style_obj["bb_outer_color"] = get_color(verified_input["style"]["bb_outer_color"])
            if "bb_inner_color" in verified_input["style"]:
                style.style_obj["bb_inner_color"] = get_color(verified_input["style"]["bb_inner_color"])
            if "top_font_background_color" in verified_input["style"]:
                style.style_obj["top_font_background_color"] = get_color(
                    verified_input["style"]["top_font_background_color"])
            if "bottom_font_background_color" in verified_input["style"]:
                style.style_obj["bottom_font_background_color"] = get_color(
                    verified_input["style"]["bottom_font_background_color"])
            if "top_font_background_outline_color" in verified_input["style"]:
                style.style_obj["top_font_background_outline_color"] = get_color(
                    verified_input["style"]["top_font_background_outline_color"])
            if "bottom_font_background_outline_color" in verified_input["style"]:
                style.style_obj["bottom_font_background_outline_color"] = get_color(
                    verified_input["style"]["bottom_font_background_outline_color"])
            if "top_font_color" in verified_input["style"]:
                style.style_obj["top_font_color"] = get_color(verified_input["style"]["top_font_color"])
            if "bottom_font_color" in verified_input["style"]:
                style.style_obj["bottom_font_color"] = get_color(verified_input["style"]["bottom_font_color"])

            style.reassess()
            return style.style_obj
        else:
            raise AlgorithmError("Please provide a valid input.")


def apply(input):
    '''
    Description: Main function.
    '''

    verified_input = verify_input(input)
    if isinstance(verified_input, list):
        output = {'output': []}
        for data in verified_input:
            img_obj, img_w, img_h = get_img_url(data["imageUrl"])

            style_obj = get_style(data, img_w, img_h)

            img_w_bb = draw_bounding_boxes(style_obj, img_obj, data["boundingBoxes"])

            imb_obj_to_data_url(img_w_bb, data["imageSaveUrl"])
            output['output'].append(data['imageSaveUrl'])
    else:
        img_obj, img_w, img_h = get_img_url(verified_input["imageUrl"])

        style_obj = get_style(verified_input, img_w, img_h)

        img_w_bb = draw_bounding_boxes(style_obj, img_obj, verified_input["boundingBoxes"])

        imb_obj_to_data_url(img_w_bb, verified_input["imageSaveUrl"])
        output = {"output": input["imageSaveUrl"]}
    return output

