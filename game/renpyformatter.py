# formatter for renpy and python code
from pygments.formatter import Formatter


class RenPyFormatter(Formatter):

    def __init__(self, **options):
        Formatter.__init__(self, **options)

        # contains (start, end) tuples that wrap the value of a
        # token to be used in the format method later
        self.styles = {}

        for token, style in self.style:
            start = end = ''
            # colors specified in hex: 'RRGGBB'
            if style['color']:
                start += '{color=#%s}' % style['color'].lower()
                end = '{/color}' + end
            for s in ['italic', 'underline']: #, 'bold' this moves the input line so won't work
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
            if ttype == lasttype:
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
