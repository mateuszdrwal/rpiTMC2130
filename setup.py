import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="rpiTMC2130",
    version="0.0.0",
    author="Mateusz Drwal",
    author_email="drwal.mateusz@gmail.com",
    description="A Raspberry Pi library for the Trinamic TMC2130 stepper motor driver",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mateuszdrwal/rpiTMC2130",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 4 - Beta",
        "Natural Language :: English",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
)
