import sys
import os.path
from setuptools import setup, Extension
from setuptools.command.build_clib import build_clib
import platform

# this package is supposed to be installed ONLY on CPython. Try to bail out
# with a meaningful error message in other cases.
if sys.implementation.name != 'cpython':
    msg = 'ERROR: Cannot install and/or update hpy on this python implementation:\n'
    msg += f'    sys.implementation.name == {sys.implementation.name!r}\n\n'
    if '_hpy_universal' in sys.builtin_module_names:
        # this is a python which comes with its own hpy implementation
        import _hpy_universal
        if hasattr(_hpy_universal, 'get_version'):
            hpy_version, git_rev = _hpy_universal.get_version()
            msg += f'This python implementation comes with its own version of hpy=={hpy_version}\n'
            msg += '\n'
            msg += 'If you are trying to install hpy through pip, consider to put the\n'
            msg += 'following in your requirements.txt, to make sure that pip will NOT\n'
            msg += 'try to re-install it:\n'
            msg += f'    hpy=={hpy_version}'
        else:
            msg += 'This python implementation comes with its own version of hpy,\n'
            msg += 'but the exact version could not be determined.\n'
        #
    else:
        # this seems to be a python which does not support hpy
        msg += 'This python implementation does not seem to support hpy:\n'
        msg += '(built-in module _hpy_universal not found).\n'
        msg += 'Please contact your vendor for more informations.'
    sys.exit(msg)


this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

if 'HPY_DEBUG_BUILD' in os.environ:
    # -fkeep-inline-functions is needed to make sure that the stubs for HPy_*
    # functions are available to call inside GDB
    EXTRA_COMPILE_ARGS = [
        '-g', '-O0', '-UNDEBUG',
        '-fkeep-inline-functions',
        #
        ## these flags are useful but don't work on all
        ## platforms/compilers. Uncomment temporarily if you need them.
        #'-Wfatal-errors',    # stop after one error (unrelated to warnings)
        #'-Werror',           # turn warnings into errors
    ]
else:
    EXTRA_COMPILE_ARGS = []

if '_HPY_DEBUG_FORCE_DEFAULT_MEM_PROTECT' not in os.environ:
    EXTRA_COMPILE_ARGS += ['-D_HPY_DEBUG_MEM_PROTECT_USEMMAP']

if platform.system() == "Windows":
    EXTRA_COMPILE_ARGS += ['/WX']
else:
    EXTRA_COMPILE_ARGS += ['-Werror']


def get_scm_config():
    """
    We use this function as a hook to generate version.h before building.
    """
    import textwrap
    import subprocess
    import pathlib
    import setuptools_scm

    version = setuptools_scm.get_version()
    try:
        gitrev = subprocess.check_output('git rev-parse --short HEAD'.split(),
                                         encoding='utf-8')
        gitrev = gitrev.strip()
    except subprocess.CalledProcessError:
        gitrev = "__UNKNOWN__"

    version_h = pathlib.Path('.').joinpath('hpy', 'devel', 'include', 'hpy', 'version.h')
    version_h.write_text(textwrap.dedent(f"""
        // automatically generated by setup.py:get_scm_config()
        #define HPY_VERSION "{version}"
        #define HPY_GIT_REVISION "{gitrev}"
    """))

    version_py = pathlib.Path('.').joinpath('hpy', 'devel', 'version.py')
    version_py.write_text(textwrap.dedent(f"""
        # automatically generated by setup.py:get_scm_config()
        __version__ = "{version}"
        __git_revision__ = "{gitrev}"
    """))

    return {}  # use the default config

HPY_EXTRA_SOURCES = [
    'hpy/devel/src/runtime/argparse.c',
    'hpy/devel/src/runtime/buildvalue.c',
    'hpy/devel/src/runtime/helpers.c',
]

HPY_CTX_SOURCES = [
    'hpy/devel/src/runtime/ctx_bytes.c',
    'hpy/devel/src/runtime/ctx_call.c',
    'hpy/devel/src/runtime/ctx_capsule.c',
    'hpy/devel/src/runtime/ctx_err.c',
    'hpy/devel/src/runtime/ctx_module.c',
    'hpy/devel/src/runtime/ctx_object.c',
    'hpy/devel/src/runtime/ctx_type.c',
    'hpy/devel/src/runtime/ctx_tracker.c',
    'hpy/devel/src/runtime/ctx_listbuilder.c',
    'hpy/devel/src/runtime/ctx_tuple.c',
    'hpy/devel/src/runtime/ctx_tuplebuilder.c',
]

HPY_INCLUDE_DIRS = [
    'hpy/devel/include',
    'hpy/universal/src',
    'hpy/debug/src/include',
    'hpy/trace/src/include',
]

HPY_EXTRA_UNIVERSAL_LIB_NAME = "hpy-extra-universal"
HPY_EXTRA_HYBRID_LIB_NAME = "hpy-extra-hybrid"
HPY_CTX_LIB_NAME = "hpy-ctx-cpython"

HPY_BUILD_CLIB_ABI_ATTR = "hpy_abi"

class build_clib_hpy(build_clib):
    """ Special build_clib command for building HPy's static libraries defined
        by 'STATIC_LIBS' below. The behavior differs in following points:
        (1) Option 'force' is set such that static libs will always be renewed.
        (2) Method 'get_library_names' always returns 'None'. This is because
            we only use this command to build static libraries for testing.
            That means, we only use them in-place. We don't need them for
            linking here.
        (3) This command consumes a custom build info key
            HPY_BUILD_CLIB_ABI_ATTR that is used to create separate build
            temp directories for each ABI. This is necessary to avoid
            incorrect sharing of (temporary) build artifacts.
        (4) This command will use the include directories from command
            'build_ext'.
    """
    def finalize_options(self):
        super().finalize_options()
        # we overwrite the include dirs and use the ones from 'build_ext'
        build_ext_includes = self.get_finalized_command('build_ext').include_dirs or []
        self.include_dirs = HPY_INCLUDE_DIRS + build_ext_includes
        self.force = 1

    def get_library_names(self):
        # We only build static libraries for testing. We just use them
        # in-place. We don't want that our extensions (i.e. 'hpy.universal'
        # etc) link to these libs.
        return None

    def build_libraries(self, libraries):
        # we just inherit the 'inplace' option from 'build_ext'
        inplace = self.get_finalized_command('build_ext').inplace
        if inplace:
            # the inplace option requires to find the package directory
            # using the build_py command for that
            build_py = self.get_finalized_command('build_py')
            lib_dir = os.path.abspath(build_py.get_package_dir('hpy.devel'))
        else:
            lib_dir = self.build_clib

        import pathlib
        for lib in libraries:
            lib_name, build_info = lib
            abi = build_info.get(HPY_BUILD_CLIB_ABI_ATTR)
            # Call super's build_libraries with just one library in the list
            # such that we can temporarily change the 'build_temp'.
            orig_build_temp = self.build_temp
            orig_build_clib = self.build_clib
            self.build_temp = os.path.join(orig_build_temp, 'lib', abi)
            self.build_clib = os.path.join(lib_dir, 'lib', abi)
            # ensure that 'build_clib' directory exists
            pathlib.Path(self.build_clib).mkdir(parents=True, exist_ok=True)
            try:
                super().build_libraries([lib])
            finally:
                self.build_temp = orig_build_temp
                self.build_clib = orig_build_clib


STATIC_LIBS = [(HPY_EXTRA_UNIVERSAL_LIB_NAME,
                {'sources': HPY_EXTRA_SOURCES,
                 HPY_BUILD_CLIB_ABI_ATTR: 'universal',
                 'macros': [('HPY_ABI_UNIVERSAL', None)]}),
               (HPY_EXTRA_HYBRID_LIB_NAME,
                {'sources': HPY_EXTRA_SOURCES,
                 HPY_BUILD_CLIB_ABI_ATTR: 'hybrid',
                 'macros': [('HPY_ABI_HYBRID', None)]}),
               (HPY_CTX_LIB_NAME,
                {'sources': HPY_EXTRA_SOURCES + HPY_CTX_SOURCES,
                 HPY_BUILD_CLIB_ABI_ATTR: 'cpython',
                 'macros': [('HPY_ABI_CPYTHON', None)]})]

EXT_MODULES = [
    Extension('hpy.universal',
              ['hpy/universal/src/hpymodule.c',
               'hpy/universal/src/ctx.c',
               'hpy/universal/src/ctx_meth.c',
               'hpy/universal/src/ctx_misc.c',
               'hpy/debug/src/debug_ctx.c',
               'hpy/debug/src/debug_ctx_cpython.c',
               'hpy/debug/src/debug_handles.c',
               'hpy/debug/src/dhqueue.c',
               'hpy/debug/src/memprotect.c',
               'hpy/debug/src/stacktrace.c',
               'hpy/debug/src/_debugmod.c',
               'hpy/debug/src/autogen_debug_wrappers.c',
               'hpy/trace/src/trace_ctx.c',
               'hpy/trace/src/_tracemod.c',
               'hpy/trace/src/autogen_trace_wrappers.c',
               'hpy/trace/src/autogen_trace_func_table.c']
              + HPY_EXTRA_SOURCES
              + HPY_CTX_SOURCES,
              include_dirs=HPY_INCLUDE_DIRS,
              extra_compile_args=[
                  # so we need to enable the HYBRID ABI in order to implement
                  # the legacy features
                  '-DHPY_ABI_HYBRID',
                  '-DHPY_DEBUG_ENABLE_UHPY_SANITY_CHECK',
                  '-DHPY_EMBEDDED_MODULES',
              ] + EXTRA_COMPILE_ARGS
              )
    ]

DEV_REQUIREMENTS = [
    "pytest",
    "pytest-xdist",
    "filelock",
]

setup(
    name="hpy",
    author='The HPy team',
    author_email='hpy-dev@python.org',
    url='https://hpyproject.org',
    license='MIT',
    description='A better C API for Python',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=['hpy.devel', 'hpy.debug', 'hpy.trace'],
    include_package_data=True,
    extras_require={
        "dev": DEV_REQUIREMENTS,
    },
    libraries=STATIC_LIBS,
    ext_modules=EXT_MODULES,
    entry_points={
        "distutils.setup_keywords": [
            "hpy_ext_modules = hpy.devel:handle_hpy_ext_modules",
        ],
    },
    cmdclass={"build_clib": build_clib_hpy},
    use_scm_version=get_scm_config,
    setup_requires=['setuptools_scm'],
    install_requires=['setuptools>=64.0'],
    python_requires='>=3.7',
)
