import Algorithmia

from .UGATIT import UGATIT
from .utils import *


config = tf.ConfigProto()

config.gpu_options.allow_growth = True
config.allow_soft_placement = True

# open session
sess = tf.Session(config=config)
        
gan = UGATIT(sess)

        # build graph
gan.build_model()
tf.global_variables_initializer().run(session=sess)

gan.load()


        # input = '/media/alex/WD RED/code/UGATIT_inf/dataset/selfie2anime/testA/*.*'
        # input = '/media/alex/WD RED/code/UGATIT_inf/dataset/selfie2anime/testA/female_281.jpg'
# input = 'https://imagevars.gulfnews.com/2019/10/29/Selfie-story_16e16cbad40_original-ratio.jpg'
# output = '/media/alex/WD RED/code/UGATIT_inf/results/test/res.jpg'





# API calls will begin at the apply() method, with the request body passed as 'input'
# For more details, see algorithmia.com/developers/algorithm-development/languages
def apply(input):
    gan.test(input["in"], input["out"])
    return "Success"
