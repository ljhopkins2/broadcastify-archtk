import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="broadcastify-archtk", # Replace with your own username
    version="0.0.1",
    author="Joseph Hopkins",
    author_email="49728392+ljhopkins2@users.noreply.github.com",
    description="The Broadcastify Archive Tool Kit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ljhopkins2/pyBArTOK",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
