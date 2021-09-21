# formatter for renpy and python code
from pygments.formatter import Formatter
from pygments.token import Error
from spellchecker import SpellChecker
from re import split as re_split


class RenPyFormatter(Formatter):

    def __init__(self, language='en', **options):
        Formatter.__init__(self, **options)

        # contains (start, end) tuples that wrap the value of a
        # token to be used in the format method later
        self.styles = {}
        self.lang = SpellChecker(language=language)
        self.do_check = True

        for token, style in self.style:
            start = end = ''
            # colors specified in hex: 'RRGGBB'
            if style['color']:
                start += '{color=#%s}' % style['color'].lower()
                end = '{/color}' + end
            # 'bold' moves the input line so won't work
            for s in ['italic', 'underline']:
                if style[s]:
                    start += '{'+s[0]+'}'
                    end = '{/'+s[0]+'}' + end
            if style['bold']:
                start += '{alpha=-0.1}'
                end = '{/alpha}' + end
            self.styles[token] = (start, end)

    def format(self, tokensource, outfile):
        # lastval is cached in case of consecutive same tokens
        lastval = ''
        lasttype = None

        for ttype, value in tokensource:
            # if the token type doesn't exist, try with parent
            while ttype not in self.styles:
                ttype = ttype.parent

            if self.do_check and ("String" in repr(ttype) or "Comment" in repr(ttype)):
                # wrap up
                if lastval:
                    stylebegin, styleend = self.styles[lasttype]
                    outfile.write(stylebegin + lastval + styleend)

                stylebegin, styleend = self.styles[ttype]

                unknown = self.lang.unknown(set(self.lang.split_words(value)))

                for part in re_split(r'\b(%s)\b' % '|'.join(unknown), value):
                    if part in unknown:
                        outfile.write(r'{a=_editor:'+part+r'}'+part+r'{/a}')
                    else:
                        outfile.write(stylebegin + part + styleend)

                lasttype = None
                lastval = ''
            elif ttype == lasttype:
                # the current token is same as last time. cache it
                lastval += value
            else:
                # not the same. wrap up
                if lastval:
                    stylebegin, styleend = self.styles[lasttype]
                    outfile.write(stylebegin + lastval + styleend)
                # set lastval/lasttype to current values
                lastval = value
                lasttype = ttype

        # write remaining in buffer to output
        if lastval:
            stylebegin, styleend = self.styles[lasttype]
            outfile.write(stylebegin + lastval + styleend)

    def get_style_defs(self, arg=None):
        if arg == "background":
            return self.style.background_color
        if arg == "highlight":
            return self.style.highlight_color
        if arg != "error" and arg != "error background":
            raise KeyError

        error = "#f11" if 'border:' in self.style.styles[Error] else self.style.styles[Error]
        error_background = self.style.background_color

        for e in error.split():
            if e[:3] == 'bg:':
                error_background = e[3:]
            elif arg == "error":
                return e

        return error_background
