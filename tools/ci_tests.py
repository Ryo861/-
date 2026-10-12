"""Run real tests and expose failures as GitHub Actions annotations."""
import sys
import unittest


def escaped(text):
    return text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def main():
    suite = unittest.defaultTestLoader.discover('tests')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    for test, detail in result.failures + result.errors:
        print(f'::error title={escaped(str(test))}::{escaped(detail)}')
    for test, reason in result.skipped:
        print(f'::error title=Skipped test::{escaped(str(test) + ": " + reason)}')
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == '__main__':
    sys.exit(main())
