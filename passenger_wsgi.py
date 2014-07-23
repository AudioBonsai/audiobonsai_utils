import sys, os
venv_dir = "/home/jesseerdmann/venvs/sandbox/"

INTERP = venv_dir + "bin/python"
if sys.executable != INTERP: os.execl(INTERP, INTERP, *sys.argv)

activation_script = venv_dir + "bin/activate_this.py"
execfile(activation_script)

os.chdir = venv_dir + "source"
sys.path.append(os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = "audiobonsai.settings"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

print os.getcwd()

from audiobonsai import settings
print settings.INSTALLED_APPS

from rootball.models import Artist
prince = Artist(name="Prince")
print prince.__unicode__()
