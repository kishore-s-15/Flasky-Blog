import os

COVERAGE = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COVERAGE = coverage.coverage(branch=True, include='app/*')
    COVERAGE.start()

import sys
import click
from flask_migrate import Migrate, upgrade

from app import create_app, db
from app.models import User, Role, Permission, Post, Comment

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, Permission=Permission, Post=Post, Comment=Comment)

@app.cli.command()
@click.option('--coverage/--no-coverage', default=False,
              help="Run tests under code coverage.")
@click.argument('test_names', nargs=-1)
def test(coverage, test_names):
    """
    Runs the unit tests
    """

    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import subprocess
        os.environ['FLASK_COVERAGE'] = '1'
        sys.exit(subprocess.call(sys.argv))
    
    import unittest
    if test_names:
        tests = unittest.TestLoader().loadTestsFromNames(test_names)
    else:
        tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COVERAGE:
        COVERAGE.stop()
        COVERAGE.save()
        print("Coverage Summary:")
        COVERAGE.report()

        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COVERAGE.html_report(directory=covdir)
        print(f"HTML version: file://{covdir}/index.html")
        COVERAGE.erase()

@app.cli.command()
@click.option('--length', default=25,
                help='Number of functions to include in the profiler report')
@click.option('--profile-dir', default=None,
                help='Directory where profiler data files are saved.')
def profile(length, profile_dir):
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                            profile_dir=profile_dir)
    app.run()

@app.cli.command()
def deploy():
    # Migrate databse to latest version
    upgrade()

    # Create or update user roles
    Role.insert_roles()

    # Ensure all users are following themselves
    User.add_self_follows()