import pathlib

from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="django-api-admin",
    version="1.1.0",
    description="Expose django.contrib.admin as a restful service. useful for adding new features to django admin or writing a new admin.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/MuhammadSalahAli/django-api-admin",
    author="Muhammad Salah",
    author_email="msmainacc0unt@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    packages=["django_api_admin"],
    include_package_data=True,
    install_requires=["django", "djangorestframework"],
)
