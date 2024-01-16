from setuptools import setup, find_packages

setup(
    name='FlawlessAPI',  # 包名
    version='0.1',  # 包的版本
    description='这是一个python高性能框架',  # 简短描述
    long_description=open('README.md').read(),  # 长描述，通常从README文件读取
    long_description_content_type='text/markdown',  # 长描述的内容类型
    author='WEN JIE',  # 作者名
    author_email='799771344@qq.com',  # 作者邮箱
    url='https://github.com/799771344/FlawlessAPI.git',  # 项目主页，通常是GitHub仓库的URL
    packages=find_packages(exclude=('tests', 'docs')),  # 项目中要包括的包，默认包括所有 src 中的包
    install_requires=[  # 运行时依赖列表
    ],
    extras_require={  # 额外的依赖列表
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
    classifiers=[  # 分类器列表
        # 'License :: OSI Approved :: MIT License',
        # 'Programming Language :: Python :: 3',
        # 'Programming Language :: Python :: 3.7',
    ],
    python_requires='>=3.6',  # 支持的Python版本范围
    # entry_points={  # 可执行的脚本/应用程序
    #     'console_scripts': [
    #         'your_command=your_package.module:function',
    #     ],
    # },
    # 其他选项...
)