import string
import warnings
warnings.filterwarnings('ignore')

versus_signs = ['v', 'vs', 'versus']
stop_words = ['the', 're', 'a', 'of', 'in', 'out', 'on', 'fw', 'for', '', 'et', 'al']


def predict(subj, unique_matters):
    mx = -100500
    k = -1
    index = -100
    for matter in unique_matters:
        k += 1
        m = Match(versus_signs=versus_signs, stop_words=stop_words, subject=subj)
        m.pre_process()
        m.companies()
        m.score_(matter)

        if m.score > mx:
            mx = m.score
            if mx > 0.5:
                index = k
    return unique_matters[index] if index != -100 else "no prediction", mx


def get_numbers(subjects, matters, unique_matters):
    corr, err = 0, 0
    no_pred = 0
    wrng = 0
    for i in range(len(subjects)):
        try:
            pred, mx = predict(str(subjects[i][0]), unique_matters)[0], predict(str(subjects[i][0]), unique_matters)[1]
            if pred == "no prediction":
                no_pred +=1
            corr += pred == matters[i][0]
            if pred != matters[i][0] and pred != "no prediction":
                wrng += 1
        except UnicodeEncodeError:
            err += 1
    # print(len(subjects))
    print('corr ', corr, 'err ', err, 'no_pred ', no_pred, 'wrng', wrng, 'subjects ', len(subjects))
    print(corr * 1. / (len(subjects) - err), no_pred * 1. / (len(subjects) - err), wrng * 1. / (len(subjects) - err))
    return corr * 1. / (len(subjects) - err), no_pred * 1. / (len(subjects) - err), wrng * 1. / (len(subjects) - err)


def get_numbers_for_manual_filing_preds(subjects, matters, unique_matters):
    corr, err = 0, 0
    no_pred = 0
    wrng = 0
    for i in range(len(subjects)):
        try:
            # print('-'*30)
            # print(subjects[i])
            # print(matters[i])
            # print(unique_matters[i])
            pred, mx = predict(str(subjects[i][0]), unique_matters[i])[0], predict(str(subjects[i][0]), unique_matters)[1]
            # print(pred)
            if pred == "no prediction":
                no_pred +=1
            corr += pred == matters[i]
            if pred != matters[i] and pred != "no prediction":
                # print('------wrong---------')
                wrng += 1
        except UnicodeEncodeError:
            err += 1
    # print(len(subjects))
    print('corr ', corr, 'err ', err, 'no_pred ', no_pred, 'wrng', wrng, 'subjects ', len(subjects))
    print(corr * 1. / (len(subjects) - err), no_pred * 1. / (len(subjects) - err), wrng * 1. / (len(subjects) - err))
    return corr * 1. / (len(subjects) - err), no_pred * 1. / (len(subjects) - err), wrng * 1. / (len(subjects) - err)


class Match(object):

    def __init__(self, versus_signs, stop_words, subject):
        translator = str.maketrans('', '', string.punctuation)
        self.versus_signs = versus_signs
        self.stop_words = stop_words
        self.subject = subject.translate(translator)
        self.sbj_list = str(self.subject).lower().split(' ')
        self.index = None
        self.comp1 = []
        self.comp2 = []
        self.score = 0
        self.C = 5.
        self.vs_score = 3.

    def pre_process(self):
        to_del = []
        for words in self.sbj_list:
            if words in self.stop_words:
                to_del.append(words)
        #                 self.sbj_list.remove(words)

        for word in to_del:
            self.sbj_list.remove(word)

    def companies(self):
        k, index = 0, 100500
        flag = False
        for word in self.sbj_list:
            if word in self.versus_signs and not flag:
                index = k
                flag = True
            elif word in self.versus_signs and flag:
                warnings.warn('Multiple versus signs were detected \
                              in {}. \n Last one is used.'.format(self.subject))
            k += 1

        self.index = index
        if index != 100500:
            self.comp1 = self.sbj_list[:index]
            self.comp2 = self.sbj_list[index + 1:]
            self.score += self.vs_score
        else:
            warnings.warn("Versus sign wasn't found in {}".format(self.subject))

    def score_(self, matter):
        translator = str.maketrans('', '', string.punctuation)
        matter = str(matter).translate(translator)
        matter = str(matter).lower().split(' ')
        for words in matter:
            if words in self.stop_words:
                matter.remove(words)

        if self.comp1 and self.comp2:
            flag1, flag2 = False, False
            for w in self.comp1:
                if w in matter:
                    flag1 = True
                    self.score += self.C / (len(matter) + 20)

            for w in self.comp2:
                if w in matter:
                    flag2 = True
                    self.score += self.C / (len(matter) + 20)

            if flag1 and flag2:
                self.score += self.C
        elif not self.comp1 and not self.comp2:
            for w in self.sbj_list:
                if w in matter:
                    self.score += self.C / (len(matter))

    # add some other things.