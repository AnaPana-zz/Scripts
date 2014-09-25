import sys
import os
import inspect

from django import forms
from DAS.models import TestJobDescription, SuiteModel

S6_ROOT = r'D:\Project'
FRAMEWORK_PATH = r'cs\AutoTest'
SUITES_PATH = r'cs\System6'

sys.path.append(os.path.join(S6_ROOT, FRAMEWORK_PATH))
sys.path.append(os.path.join(S6_ROOT, SUITES_PATH))

class AddSuiteForm(forms.Form):
    """
    Suite name is obtained from the uploaded file by truncating ".py" extension.
    Also, the suite can be added to several test job descriptions.
    """
    tjdsAll = ((tjd.pk, tjd.name) for tjd in TestJobDescription.objects.all())
    suiteFile = forms.FileField(required = True, label = 'Choose suite file')
    suiteType = forms.ChoiceField(required = True, label = 'Choose suite type',
                                  choices = SuiteModel.SUITE_TYPE_CHOICES, initial = SuiteModel.EXTENDED)
    tjds = forms.MultipleChoiceField(required = True, label = 'Choose test job descriptions',
                                     choices = tjdsAll)
    suiteDescription = forms.CharField(required=False, label = 'Write suite description (leave blank for generating automatically).',
                                       widget=forms.Textarea(
                                           attrs={'rows': 3, 'cols': 40, 'placeholder': 'Suite description'}
                                       ))

    def clean(self, *args, **kwargs):
        super(AddSuiteForm, self).clean(*args, **kwargs)
        suite_file = self.cleaned_data.get('suiteFile')
        if not suite_file:
            raise forms.ValidationError("")
        suite_description = self.cleaned_data.get('suiteDescription')
        suiteName = suite_file.name.replace('.py', '')
        # validate suite name
        try:
            SuiteModel.objects.get(name=suiteName)
        except SuiteModel.DoesNotExist:
            pass
        else:
            raise forms.ValidationError("Suite '%s' is already in DB." % suiteName)

        # validate suite description
        if not suite_description:
            try:
                imported_suite = self.save_and_import_uploaded_suite(suite_file)
            except ImportError:
                raise forms.ValidationError("Can't import suite module and get its description. Please fill 'description' field manually.")
            else:
                suite_description = self.get_suite_description(imported_suite)
                self.cleaned_data['suiteDescription'] = suite_description

        return self.cleaned_data


    @staticmethod
    def save_and_import_uploaded_suite(f):
        """
        Saves suite file on server in SUITES_PATH and imports it.
        :param f: uploaded suite file through suite form
        :return: imported suite file
        """
        suite_file = open(os.path.join(S6_ROOT, SUITES_PATH, f.name), 'wb+')
        for chunk in f.chunks():
            suite_file.write(chunk)
        suite_file.close()
        return __import__(f.name.replace('.py', ''))


    @staticmethod
    def get_suite_description(suite):
        """
        Gets suite class and methods doc strings.
        :param suite: imported suite file
        :return: suite description as string
        """
        SUITE_NAME_DIVIDER = '*'
        SUITE_METHOD_DIVIDER = '-'
        suite_description = ''
        suite_name = suite.__name__
        suite_name_len = len(suite.__name__)

        suite_description += '\n'.join([SUITE_NAME_DIVIDER*suite_name_len, suite_name,
                                        SUITE_NAME_DIVIDER*suite_name_len, '\n'])

        try:
            class_description = suite.Suite.__doc__
        except AttributeError:
            return ''

        if class_description:
            suite_description += '\n'.join(['Description: ', class_description.strip(), '\n'])

        suite_description += "Methods:\n\n"
        for method in inspect.getmembers(suite.Suite, predicate=inspect.ismethod):
            method_name = method[0]
            method_name_len = len(method_name)
            if method_name.startswith('test'):
                suite_description += '\n'.join([SUITE_METHOD_DIVIDER*method_name_len, method_name,
                                                SUITE_METHOD_DIVIDER*method_name_len, ''])
                method_description = getattr(suite.Suite, method_name).__doc__
                if method_description:
                    suite_description += method_description.strip()
                else:
                    suite_description += "No description."
                suite_description += "\n\n"
        return suite_description
