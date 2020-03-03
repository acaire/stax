<div align="center">
  <img src="./stax.svg" alt="stax">
</div>

# Stax
`Stax` is a Python tool to manage every aspect of Cloudformation Stacks.

<a href="https://github.com/acaire/stax/actions"><img alt="Actions Status" src="https://github.com/acaire/stax/workflows/Test/badge.svg"></a>
<a href="https://github.com/acaire/stax/blob/master/LICENSE"><img alt="License: MIT" src="https://img.shields.io/github/license/acaire/stax"></a>
<a href="https://pypi.org/project/stax/"><img alt="PyPI" src="https://img.shields.io/pypi/v/stax"></a>

<br/>

Features
========
* Apply source controlled changes to Cloudformation stacks in multiple accounts and regions

<br/>

Install
=======
## Homebrew:
```
   brew tap acaire/taps/stax git@github.com:acaire/homebrew-taps.git
   brew install acaire/taps/stax
```

## PyPI:
```
  pip install stax
```

<br/>

Developing on Stax:
===================
```
# Install Python 3.8 and direnv
brew install python@3.8 direnv

# Make direnv work at startup according to your shell
echo 'eval "$(direnv hook bash )"' >> ~/.zshrc
echo 'eval "$(direnv hook bash )"' >> ~/.bash_profile

# Review .envrc and allow accordingly, which activates the virtualenv
direnv allow

# Add pre-commit hooks
pip install pre-commit
pre-commit install

# Install editable version
pip install -e .

# Run stax
stax
```

<br/>
