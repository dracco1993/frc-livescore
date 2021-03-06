import cv2
import numpy as np
import pytesseract
import re
import imutils
import pkg_resources
from PIL import Image

from details import Alliance, OngoingMatchDetails


class Livescore:
    def __init__(self, options={}):
        local_path = pkg_resources.resource_filename(__name__, 'tessdata')
        template_path = pkg_resources.resource_filename(__name__, 'templates')

        templates = {
            'scoreboard': template_path + '/scoreboard.png',
            'scores': template_path + '/scores.png',
            'time': template_path + '/time.png',
            'top': template_path + '/top.png'
        }

        if 'scoreboard' not in options:
            self.TEMPLATE_SCOREBOARD = cv2.imread(templates['scoreboard'], 0)
        else:
            self.TEMPLATE_SCOREBOARD = options['scoreboard']

        if 'scores' not in options:
            self.TEMPLATE_SCORES = cv2.imread(templates['scores'], 0)
        else:
            self.TEMPLATE_SCORES = options['scores']

        if 'time' not in options:
            self.TEMPLATE_TIME = cv2.imread(templates['time'], 0)
        else:
            self.TEMPLATE_TIME = options['time']

        if 'top' not in options:
            self.TEMPLATE_TOP = cv2.imread(templates['top'], 0)
        else:
            self.TEMPLATE_TOP = options['top']

        self.WHITE_LOW = np.array([185, 185, 185])
        self.WHITE_HIGH = np.array([255, 255, 255])

        self.BLACK_LOW = np.array([0, 0, 0])
        self.BLACK_HIGH = np.array([105, 105, 135])

        self.local_path = local_path

    def matchTemplate(self, img, template):
        res = cv2.matchTemplate(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY),
                                template,
                                cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        top_left = max_loc
        bottom_right = (top_left[0] + template.shape[1],
                        top_left[1] + template.shape[0])

        return top_left, bottom_right

    def getScoreboard(self, img):
        template_width = self.TEMPLATE_SCOREBOARD.shape[1]
        img_width = img.shape[1]
        template = imutils.resize(self.TEMPLATE_SCOREBOARD,
                                  width=int(template_width/1280.0*img_width))
        top_left, bottom_right = self.matchTemplate(img, template)

        return img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    def getTopBar(self, img):
        template_width = self.TEMPLATE_TOP.shape[1]
        img_width = img.shape[1]
        template = imutils.resize(self.TEMPLATE_TOP,
                                  width=int(template_width/1280.0*img_width))
        top_left, bottom_right = self.matchTemplate(img, template)

        located = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        h, w = located.shape[:2]

        return located[:, int(w*0.125):int(w*0.5)]

    def getTimeArea(self, img):
        template_width = self.TEMPLATE_TIME.shape[1]
        img_width = img.shape[1]
        template = imutils.resize(self.TEMPLATE_TIME,
                                  width=int(template_width/1280.0*img_width))
        top_left, bottom_right = self.matchTemplate(img, template)

        located = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        h, w = located.shape[:2]

        return located[int(h*0.16):int(h*0.84), int(w*0.42):int(w*0.58)]

    def getScoreArea(self, img):
        template_width = self.TEMPLATE_SCORES.shape[1]
        img_width = img.shape[1]
        template = imutils.resize(self.TEMPLATE_SCORES,
                                  width=int(template_width/1280.0*img_width))
        top_left, bottom_right = self.matchTemplate(img, template)

        return img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

    def getRedScoreArea(self, img):
        score_area = self.getScoreArea(img)
        return score_area[:, int((score_area.shape[1]/2)*0.05):int((score_area.shape[1]/2)*0.95)]

    def getBlueScoreArea(self, img):
        score_area = self.getScoreArea(img)
        return score_area[:, int((score_area.shape[1]/2)*1.05):int(score_area.shape[1]*0.95)]

    def read(self, img):
        scoreboard = self.getScoreboard(img)

        top_cropped = self.getTopBar(scoreboard)
        time_cropped = self.getTimeArea(scoreboard)
        red_cropped = self.getRedScoreArea(scoreboard)
        blue_cropped = self.getBlueScoreArea(scoreboard)

        top_cropped = cv2.inRange(top_cropped,
                                  self.BLACK_LOW,
                                  self.BLACK_HIGH)
        time_cropped = cv2.inRange(time_cropped,
                                   self.BLACK_LOW,
                                   self.BLACK_HIGH)
        blue_cropped = cv2.inRange(blue_cropped,
                                   self.WHITE_LOW,
                                   self.WHITE_HIGH)
        red_cropped = cv2.inRange(red_cropped,
                                  self.WHITE_LOW,
                                  self.WHITE_HIGH)

        long_match = pytesseract.image_to_string(Image.fromarray(top_cropped),
                                                 config='--psm 7 -l consolas \
                                                         --tessdata-dir {}'.format(self.local_path)).strip()
        match = None
        m = re.search('([a-zA-z]+) ([1-9]+)( of ...?)?', long_match)
        if m is not None:
            match = m.group(1) + ' ' + m.group(2)

        config = '--psm 8 -l consolas --tessdata-dir {} \
                  -c tessedit_char_whitelist=1234567890 digits'.format(self.local_path)

        time_remaining = pytesseract.image_to_string(
                                            Image.fromarray(time_cropped),
                                            config=config).strip()
        blue_score = pytesseract.image_to_string(
                                            Image.fromarray(blue_cropped),
                                            config=config).strip()
        red_score = pytesseract.image_to_string(
                                            Image.fromarray(red_cropped),
                                            config=config).strip()

        return OngoingMatchDetails(match=match,
                                   time=time_remaining,
                                   red=Alliance(score=red_score),
                                   blue=Alliance(score=blue_score))
