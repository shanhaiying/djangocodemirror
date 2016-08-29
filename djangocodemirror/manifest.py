# -*- coding: utf-8 -*-
"""
CodeMirror manifest
===================

Every assets paths should be relative path to your static directory. In fact it
depends how you will use them, but commonly it should be so.

Todo:
    Describe config format.
"""
import copy, json

from django.conf import settings


class NotRegistered(KeyError):
    pass


class UnknowConfig(KeyError):
    pass


class UnknowMode(KeyError):
    pass


class UnknowTheme(KeyError):
    pass


class CodeMirrorManifest(object):
    """
    CodeMirror config and assets manifest

    Attributes:
        registry (dict): Configuration registry.
        default_internal_config (dict): Default editor internal parameters.
        _internal_only (list): Names of internal parameters only that will not
            be passed into codemirror parameters.
    """
    default_internal_config = {
        'mode': None, # Current mode, automatically added to 'modes'
        'modes': [], # Enabled modes
        'addons': [], # Addons filepaths to load
        'themes': [], # Themes filepaths to load
        'css_bundle_name': None, # CSS bundle name to fill
        'js_bundle_name': None, # Javascript bundle name to fill
    }

    _internal_only = ['modes', 'addons', 'themes', 'css_bundle_name',
                      'js_bundle_name']

    def __init__(self):
        self.registry = {}

    def register(self, name):
        """
        Register configuration for an editor instance.

        Arguments:
            name (string): Config name from available ones in
                ``settings.CODEMIRROR_SETTINGS``.

        Returns:
            dict: Registred config dict.
        """
        if name not in settings.CODEMIRROR_SETTINGS:
            raise UnknowConfig(("Given config name '{}' does not exists in "
                                 "'settings.CODEMIRROR_SETTINGS'.").format(
                                     name
                                ))

        parameters = copy.deepcopy(self.default_internal_config)
        parameters.update(copy.deepcopy(
            settings.CODEMIRROR_SETTINGS[name]
        ))

        # Add asset bundles name
        css_template_name = settings.CODEMIRROR_BUNDLES_CSS_NAME
        parameters['css_bundle_name'] = css_template_name.format(
            settings_name=name
        )
        js_template_name = settings.CODEMIRROR_BUNDLES_JS_NAME
        parameters['js_bundle_name']= js_template_name.format(
            settings_name=name
        )

        # If mode is none but modes is not empty, use the first modes
        # item as current mode (this is the codemirror behavior, make it
        # python explicit)
        if not parameters.get('mode') and len(parameters.get('modes', []))>0:
            parameters['mode'] = self.resolve_mode(parameters['modes'][0])
        # Else if mode is not empty, add it as first item in modes
        elif 'mode' in parameters:
            if isinstance(parameters['mode'], basestring):
                parameters['modes'] = [parameters['mode']] + parameters['modes']

        self.registry[name] = parameters

        return parameters

    def autoregister(self):
        """
        Register every configuration from ``settings.CODEMIRROR_SETTINGS``.
        """
        for name in settings.CODEMIRROR_SETTINGS:
            self.register(name)

    def resolve_mode(self, name):
        """
        From given mode name, return mode file path from
        ``settings.CODEMIRROR_MODES`` map.

        Raises:
            KeyError: When given name does not exist in
            ``settings.CODEMIRROR_MODES``.

        Returns:
            string: Mode file path.
        """
        if name not in settings.CODEMIRROR_MODES:
            raise UnknowMode(("Given config name '{}' does not exists in "
                              "'settings.CODEMIRROR_MODES'.").format(name))

        return settings.CODEMIRROR_MODES.get(name)

    def resolve_theme(self, name):
        """
        From given theme name, return theme file path from
        ``settings.CODEMIRROR_THEMES`` map.

        Raises:
            KeyError: When given name does not exist in
            ``settings.CODEMIRROR_THEMES``.

        Returns:
            string: Theme file path.
        """
        if name not in settings.CODEMIRROR_THEMES:
            raise UnknowTheme(("Given theme name '{}' does not exists in "
                               "'settings.CODEMIRROR_THEMES'.").format(name))

        return settings.CODEMIRROR_THEMES.get(name)

    def get_configs(self, name=None):
        """
        Returns registred configurations.

        * If ``name`` argument is not given, default behavior is to return
          every config from all registred config;
        * If ``name`` argument is given, just return its config and nothing
          else;

        Arguments:
            name (string): Specific configuration name to return.

        Returns:
            dict: Configurations.
        """
        if name:
            if name not in self.registry:
                raise NotRegistered(("Given config name '{}' "
                                    "is not registered.").format(name))

            return {name: self.registry[name]}
        return self.registry

    def get_config(self, name):
        """
        Return a registred configuration for given config name.

        Arguments:
            name (string): A registred config name.

        Returns:
            dict: Configuration.
        """
        if name not in self.registry:
            raise NotRegistered(("Given config name '{}' "
                                 "is not registered.").format(name))

        return copy.deepcopy(self.registry[name])

    def get_codemirror_config(self, name):
        """
        Return CodeMirror configuration for given config name.

        Arguments:
            name (string): Config name from available ones in
                ``settings.CODEMIRROR_SETTINGS``.

        Returns:
            dict: Configuration.
        """
        config = self.get_config(name)

        for k,v in config.items():
            if k in self._internal_only:
                del config[k]

        # Default mode value is None, if so we dont expose it
        if not config['mode']:
            del config['mode']

        return config

    def js(self, name=None):
        """
        Returns all needed Javascript filepaths for given config name (if
        given) or every registred config instead (if no name is given).

        Arguments:
            name (string): Specific config name to use instead of all.

        Returns:
            list: List of Javascript file paths.
        """
        filepaths = copy.copy(settings.CODEMIRROR_BASE_JS)

        configs = self.get_configs(name)

        # Addons first
        for name,opts in configs.items():
            for item in opts.get('addons', []):
                if item not in filepaths:
                    filepaths.append(item)

        # Process modes
        for name,opts in configs.items():
            for item in opts['modes']:
                resolved = self.resolve_mode(item)
                if resolved not in filepaths:
                    filepaths.append(resolved)

        return filepaths

    def css(self, name=None):
        """
        Returns all needed CSS filepaths for given config name (if
        given) or every registred config instead (if no name is given).

        Arguments:
            name (string): Specific config name to use instead of all.

        Returns:
            list: List of CSS file paths.
        """
        filepaths = copy.copy(settings.CODEMIRROR_BASE_CSS)

        configs = self.get_configs(name)

        # Process theme names
        for name,opts in configs.items():
            for item in opts.get('themes', []):
                # Uniqueness
                resolved = self.resolve_theme(item)
                if resolved not in filepaths:
                    filepaths.append(resolved)

        return filepaths