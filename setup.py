from setuptools import setup

extras = {
    'docs': [
        'sphinx==4.4.0',
        'sphinxcontrib_trio==1.1.2',
        'sphinxcontrib-websupport',
        'typing-extensions',
    ],
}

setup(
    name="winerp",
    version="1.4.0",
    description="Websocket based IPC for discord.py bots",
    long_description="...",
    long_description_content_type="text/markdown",
    url="https://github.com/BlackThunder01001/winerp",
    project_urls={
        "Bug Tracker": "https://github.com/BlackThunder01001/winerp/issues",
        "Documentation": "https://winerp.readthedocs.io/en/latest/",
    },
    author="BlackThunder",
    author_email="nouman0103@gmail.com",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Operating System :: OS Independent",
        "Typing :: Typed",
        
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
    install_requires=["websockets", "websocket-server", "orjson"],
    extra_requires=extras,
    python_requires=">=3.6",
)
