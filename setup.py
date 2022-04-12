from setuptools import setup

setup(
    name="winerp",
    version="1.1.1",
    description="Websocket based IPC for discord.py bots",
    long_description="...",
    long_description_content_type="text/markdown",
    url="https://github.com/BlackThunder01001/winerp",
    project_urls={
        "Bug Tracker": "https://github.com/BlackThunder01001/winerp/issues",
    },
    author="BlackThunder",
    author_email="nouman0103@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Operating System :: OS Independent",
        
    ],
    packages=["winerp"],
    package_data={
     'winerp.lib': ['*'],
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'winerp=winerp.__main__:run',
            ]
        },
    install_requires=["websockets", "websocket-server"],
    python_requires=">=3.6",
)
