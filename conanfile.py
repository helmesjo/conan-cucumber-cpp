#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools
from conans.errors import ConanException
import os
import re

def replace(file, pattern, subst):
    # Read contents from file as a single string
    file_handle = open(file, 'r')
    file_string = file_handle.read()
    file_handle.close()

    # Use RE package to allow for replacement (also allowing for (multiline) REGEX)
    file_string = (re.sub(pattern, "{} # <-- Line edited by conan package -->".format(subst), file_string))

    # Write contents to file.
    # Using mode 'w' truncates the file.
    file_handle = open(file, 'w')
    file_handle.write(file_string)
    file_handle.close()

class LibnameConan(ConanFile):
    name = "cucumber-cpp"
    version = "0.5"
    description =   "Cucumber-Cpp, formerly known \
                    as CukeBins, allows Cucumber to support \
                    step definitions written in C++."
    url = "https://github.com/helmesjo/conan-cucumber-cpp"
    homepage = "https://github.com/cucumber/cucumber-cpp"
    author = "helmesjo <helmesjo@gmail.com>"
    # Indicates License type of the packaged library
    license = "MIT"

    # Packages the license for the conanfile.py
    exports = ["LICENSE.md"]

    # Remove following lines if the target lib does not use cmake.
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"

    # Options may need to change depending on the packaged library.
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False], 
        "fPIC": [True, False],
        "test_framework": ["boost", "gtest"],
        "cuke_disable_e2e_tests": [True, False],
        "cuke_disable_qt": [True, False],
        "cuke_disable_unit_tests": [True, False],
        "cuke_enable_examples": [True, False],
        "valgrind_tests": [True, False],
    }
    default_options = (
        "shared=False", 
        "fPIC=True",
        "test_framework=gtest",
        "cuke_disable_e2e_tests=True",
        "cuke_disable_qt=True",
        "cuke_disable_unit_tests=True",
        "cuke_enable_examples=False",
        "valgrind_tests=False",
    )

    requires_boost_test = False
    requires_gtest = False

    # Custom attributes for Bincrafters recipe conventions
    source_subfolder = "source_subfolder"
    build_subfolder = "build_subfolder"

    requires = ( "boost/1.66.0@conan/stable" )

    def requirements(self):
        if self.requires_gtest:
            self.requires.add("gtest/1.8.0@bincrafters/stable")
            self.options['gtest'].build_gmock = True
    
    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def configure(self):
        if self.options.test_framework == "boost":
            raise ConanException("Boost testing framework is currently not supported.")
        if not self.options.cuke_disable_qt:
            raise ConanException("Qt is currently not supported.")

        if self.settings.compiler != 'Visual Studio':
            self.options['boost'].add_option('fPIC', 'True')

        # Boost.Test fails to link. Skip for now.
        self.requires_boost_test = False # self.options.test_framework == "boost" or not self.options.cuke_disable_unit_tests
        self.requires_gtest = self.options.test_framework == "gtest" or not self.options.cuke_disable_unit_tests

    def patch_cmake_file(self, root_cmakelists_file_path):
        self.output.info("Patching {}/CMakeLists.txt: {}".format(self.name, root_cmakelists_file_path))
        # Remove hard-coded decision making of how to link boost.
        replace(root_cmakelists_file_path, r"((?i)\bset\b\(*.Boost_USE_STATIC_LIBS .*\))", r"# \1")
        replace(root_cmakelists_file_path, r"((?i)\bset\b\(*.Boost_USE_STATIC_RUNTIME .*\))", r"# \1")
        # Forcefully insert 'add_definitions(-DBOOST_ALL_NO_LIB)' to disable boost auto-linking
        # NOTE: Need this because it is defined as a cmake-variable implicitly from the boost requirement, but not as a preprocessor define...
        replace(root_cmakelists_file_path, r"((?i)\bcmake_minimum_required\b\(*..*\))", r"\1\nadd_definitions(-DBOOST_ALL_NO_LIB)")

    def source(self):
        source_url = "https://github.com/cucumber/cucumber-cpp"
        tools.get("{0}/archive/v{1}.tar.gz".format(source_url, self.version))
        extracted_dir = self.name + "-" + self.version

        # Rename to "source_subfolder" is a convention to simplify later steps
        os.rename(extracted_dir, self.source_subfolder)
        # Remove lines messing up "find_package(Boost ...)"
        self.patch_cmake_file(os.path.join(self.source_subfolder ,"CMakeLists.txt"))

    def configure_cmake(self):
        cmake = CMake(self, set_cmake_flags=True)
        if self.settings.os != 'Windows':
            cmake.definitions['CMAKE_POSITION_INDEPENDENT_CODE'] = self.options.fPIC

        def add_cmake_option(option, value):
            var_name = "{}".format(option).upper()
            value_str = "{}".format(value)
            var_value = "ON" if value_str == 'True' else "OFF" if value_str == 'False' else value_str 
            cmake.definitions[var_name] = var_value

        for attr, _ in self.options.iteritems():
            value = getattr(self.options, attr)
            add_cmake_option(attr, value)

        cmake.definitions['BUILD_SHARED_LIBS'] = self.options.shared
        cmake.definitions['CUKE_DISABLE_BOOST_TEST'] = not self.requires_boost_test
        cmake.definitions['CUKE_DISABLE_GTEST'] = not self.requires_gtest
        cmake.definitions['CUKE_USE_STATIC_BOOST'] = not self.options['boost'].shared

        # Boost
        cmake.definitions['BOOST_ROOT'] = self.deps_cpp_info['boost'].rootpath

        # GTest
        if self.requires_gtest:
            cmake.definitions['CUKE_USE_STATIC_GTEST'] = not self.options['gtest'].shared
            cmake.definitions['GTEST_ROOT'] = self.deps_cpp_info['gtest'].rootpath
            cmake.definitions['GMOCK_ROOT'] = self.deps_cpp_info['gtest'].rootpath

        cmake.configure(source_folder=self.source_subfolder, build_folder=self.build_subfolder)
        return cmake

    def build(self):
        cmake = self.configure_cmake()
        cmake.build()

        tests_enabled = not self.options.cuke_disable_unit_tests or not self.options.cuke_disable_e2e_tests

        if tests_enabled:
            self.output.info("Running {} tests".format(self.name))
            cmake.test()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self.source_subfolder)

        generated_source = os.path.join(self.build_subfolder, "src")
        self.copy(pattern="{}/*".format(self.name), dst="include", src=generated_source, keep_path=True)

        include_folder = os.path.join(self.source_subfolder, "include")
        self.copy(pattern="*", dst="include", src=include_folder)
        self.copy(pattern="*.dll", dst="bin", keep_path=False)
        self.copy(pattern="*.lib", dst="lib", keep_path=False)
        self.copy(pattern="*.a", dst="lib", keep_path=False)
        self.copy(pattern="*.so*", dst="lib", keep_path=False)
        self.copy(pattern="*.dylib", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
