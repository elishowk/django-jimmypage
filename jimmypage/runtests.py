import sys
from django.conf import settings
from django.test.utils import get_runner

def runtests():
    runner = get_runner(settings)(verbosity=1, interactive=True)
    failures = runner.run_tests(['jimmypage'])
    sys.exit(bool(failures))

if __name__ == "__main__":
    runtests()
