from setuptools import find_packages, setup

setup(
    name="py7dtd",
    version="0.1",
    packages=find_packages(where="src", exclude=["tests*"]),
    package_dir={"": "src"},
    license="MIT",
    description="Collection of 7 Days to Die bots, scripts and hacks",
    keywords=["7dtd", "bots", "hacks", "scripts"],
    long_description=open("README.md").read(),
    install_requires=[
        "tensorflow==2.4.2",
        "tensorflow-gpu==2.5.1",
        "keras==2.4.3",
        "numpy==1.19.3",
        "pillow==8.3.2",
        "scipy==1.4.1",
        "h5py==2.10.0",
        "matplotlib==3.3.2",
        "opencv-python",
        "keras-resnet==0.2.0",
        "imageai==2.1.6",
        "labelImg==1.8.3",
        "pywin32==301",
    ],
    url="https://github.com/tassoneroberto/py7dtd",
    author="Roberto Tassone",
    author_email="tassoneroberto@outlook.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
    entry_points={
        "console_scripts": [
            "py7dtd_crack_passcode = py7dtd.scripts.crack_passcode:main",
            "py7dtd_auto_shooting = py7dtd.bots.auto_shooting:main",
        ],
    },
)
