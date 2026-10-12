# coding: utf-8
"""Small native settings window. Controls edit a draft until Apply is pressed."""


def _ae_make_window(owner):
    from carbonui import uiconst as C
    from carbonui.control.window import Window
    from carbonui.control.button import Button
    from carbonui.control.checkbox import Checkbox
    from carbonui.control.slider import Slider
    from carbonui.control.collapseGroup import CollapseGroup
    from carbonui.control.scrollContainer import ScrollContainer
    from carbonui.primitives.container import Container
    from carbonui.primitives.fill import Fill
    from eve.client.script.ui.control.eveLabel import Label

    teal = (0.32, 0.88, 0.86, 1.0)
    white = (0.88, 0.93, 0.95, 1.0)
    muted = (0.58, 0.68, 0.73, 1.0)
    amber = (1.0, 0.68, 0.31, 1.0)
    border = (0.24, 0.39, 0.43, 0.5)
    fields = ('depletionStyle', 'dustEnabled', 'smoothShrink', 'resizeDurationMs',
              'dustIntensity', 'dustLifetimeMs', 'depletionDurationMs',
              'dustMaxConcurrent')
    styles = (
        ('dust', 'Dust & crumble',
         'The last remnant shrinks away under a lingering dust cloud.'),
        ('burn', 'Burning',
         'Keep EVE\'s original burning dissolve and its native timing.'),
        ('hybrid', 'Burn + dust',
         'Keep the original burning dissolve, with surface dust as well.'),
        ('quiet', 'Quiet finish',
         'The last remnant shrinks away quietly, without depletion dust.'))

    def label(parent, text, **kwargs):
        kwargs.setdefault('align', C.TOTOP)
        kwargs.setdefault('fontsize', 14)
        kwargs.setdefault('state', C.UI_DISABLED)
        kwargs.setdefault('color', white)
        return Label(parent=parent, text=text, **kwargs)

    class MenuButton(Button):
        def get_intrinsic_width(self):
            if self.align == C.TOTOP:
                return 0
            return max(86, Button.get_intrinsic_width(self))

        def get_intrinsic_height(self):
            return 38

        def PrepareLabel(self):
            Button.PrepareLabel(self)
            self._label.fontsize = 14

    class AsteroidErosionWindow(Window):
        default_windowID = 'evejsAsteroidErosion'
        default_caption = 'Asteroid Erosion'
        default_width = 560
        default_height = 760
        default_minSize = (500, 600)
        default_isStackable = False
        default_scope = C.SCOPE_INGAME

        def ApplyAttributes(self, attributes):
            Window.ApplyAttributes(self, attributes)
            self.owner = owner
            self._loading = True
            self._saving = False
            self._characterGeneration = owner.character_generation
            self._characterID = owner.preferences.storage()[0]
            self._snapshot = self.ReadSnapshot()
            self._draft = dict(self._snapshot)
            self._sliders = {}
            self._sliderCallbacks = {}
            self._checks = {}
            self._readouts = {}
            self._styleButtons = {}
            self._styleLines = {}
            self._styleTints = {}
            Fill(bgParent=self.content, color=(0.025, 0.043, 0.055, 0.98))

            head = Container(parent=self.content, align=C.TOTOP, height=72,
                             padding=(20, 14, 20, 8))
            label(head, 'ASTEROID EROSION', fontsize=20, bold=True, color=teal)
            label(head, 'Personal visual settings', fontsize=13, color=muted,
                  padTop=5)
            Fill(parent=head, align=C.TOBOTTOM, height=1, color=border)

            footer = Container(parent=self.content, align=C.TOBOTTOM, height=66,
                               padding=(20, 12, 20, 12))
            self.applyButton = MenuButton(parent=footer, align=C.TORIGHT,
                                          label='Apply', func=self.ApplyDraft)
            MenuButton(parent=footer, align=C.TORIGHT, padRight=8,
                       label='Close', func=self.CloseByUser, args=())
            stateBox = Container(parent=footer, align=C.TOALL, padRight=12)
            self.saveState = label(stateBox, 'No changes', fontsize=12,
                                   color=muted, maxLines=2, padTop=4)
            # Children below attach directly to mainCont. Pin its alignment:
            # the native ScrollContainer only infers a stretching alignment
            # when children pass through its own redirected children list.
            scroll = ScrollContainer(parent=self.content, align=C.TOALL,
                                     alignMode=C.TOTOP, padding=(20, 0, 20, 0))
            self.scroll = scroll
            body = scroll.mainCont

            self.Heading(body, 'When a rock is depleted')
            for offset in (0, 2):
                row = Container(parent=body, align=C.TOTOP, height=44)
                for index, (key, text, description) in enumerate(styles[offset:offset + 2]):
                    cell = Container(parent=row, align=C.TOLEFT_PROP, width=0.5,
                                     padRight=4 if index == 0 else 0,
                                     padLeft=4 if index else 0)
                    button = MenuButton(parent=cell, align=C.TOTOP, label=text,
                                        func=self.StyleCallback(key))
                    self._styleButtons[key] = button
                    self._styleTints[key] = Fill(bgParent=button,
                        color=(0.12, 0.65, 0.65, 0.12), state=C.UI_HIDDEN)
                    self._styleLines[key] = Fill(parent=button, align=C.TOBOTTOM,
                        height=2, color=teal, state=C.UI_HIDDEN)
            descriptionBox = Container(parent=body, align=C.TOTOP, height=60,
                                       padding=(0, 8, 0, 8))
            self.styleDescription = label(descriptionBox, '', color=muted,
                                          fontsize=13, maxLines=3)
            self.Divider(body)
            self.Heading(body, 'While mining')
            self.AddCheckbox(body, 'dustEnabled', 'Surface dust',
                             'Dust follows the size of the rock.')
            self.AddSlider(body, 'dustIntensity', 'Dust strength', 0.0, 3.0,
                           self.StrengthText)
            self.AddCheckbox(body, 'smoothShrink', 'Smooth shrinking',
                             'Ease each mining cycle instead of changing size instantly.')
            self.AddSlider(body, 'resizeDurationMs', 'Shrink time', 0, 3000,
                           self.MillisecondsText, integer=True)
            self.Divider(body)

            self.fineTuning = CollapseGroup(parent=body, align=C.TOTOP,
                                           text='Fine tuning')
            advanced = self.fineTuning.mainCont
            self.AddSlider(advanced, 'dustLifetimeMs', 'Dust lifetime', 300, 4000,
                           self.SecondsText, integer=True)
            self.AddSlider(advanced, 'depletionDurationMs', 'Final shrink time',
                           0, 2000, self.MillisecondsText, integer=True)
            label(advanced, 'Burning styles use EVE\'s original animation timing.',
                  fontsize=12, color=muted, padBottom=10, maxLines=2)
            self.AddSlider(advanced, 'dustMaxConcurrent', 'Maximum dusty rocks',
                           1, 64, self.IntegerText, integer=True)
            label(advanced, 'Higher limits can cost more GPU time.', fontsize=12,
                  color=muted, padBottom=8, maxLines=2)
            self.fineTuning.SetCollapsed(True)
            label(body, 'Preferences apply to this character on this client. '
                        'Ore quantities and mining rules stay server-side.',
                  fontsize=12, color=muted, padTop=14, padBottom=16, maxLines=3)
            self._loading = False
            self.RefreshControls()
            # Native Window.OnUIRefresh recreates through Class.Open, bypassing
            # the manager's open_window. Keep session cleanup attached to it.
            owner.window = self

        def ReadSnapshot(self):
            values = owner.settings_snapshot()
            return dict((key, values[key]) for key in fields)

        def Heading(self, parent, text):
            box = Container(parent=parent, align=C.TOTOP, height=36,
                            padding=(0, 9, 0, 7))
            label(box, text, bold=True, fontsize=14)

        def Divider(self, parent):
            box = Container(parent=parent, align=C.TOTOP, height=12, padTop=5)
            Fill(parent=box, align=C.TOTOP, height=1, color=border,
                 state=C.UI_DISABLED)

        def AddCheckbox(self, parent, key, title, hint):
            box = Container(parent=parent, align=C.TOTOP, height=54)
            control = Checkbox(parent=box, align=C.TOTOP, text=title,
                checked=bool(self._draft[key]), settingsPath=None,
                callback=self.CheckboxCallback(key))
            label(box, hint, fontsize=12, color=muted, padLeft=26,
                  padTop=1, maxLines=2)
            self._checks[key] = control

        def AddSlider(self, parent, key, title, minimum, maximum, formatter,
                      integer=False):
            box = Container(parent=parent, align=C.TOTOP, height=65,
                            padTop=3)
            titleRow = Container(parent=box, align=C.TOTOP, height=23)
            self._readouts[key] = label(titleRow, formatter(self._draft[key]),
                align=C.TOPRIGHT, fontsize=13, color=teal)
            label(titleRow, title, fontsize=13)
            # Native signals.Signal weakly retains free functions. The window
            # must own these closures for the complete lifetime of the controls.
            callback = self.SliderCallback(key, formatter, integer)
            self._sliderCallbacks[key] = callback
            control = Slider(parent=box, align=C.TOTOP, minValue=minimum,
                maxValue=maximum, value=self._draft[key], isInteger=integer,
                callback=callback, on_dragging=callback,
                mouseWheelEnabled=False, padTop=5)
            self._sliders[key] = control

        @staticmethod
        def StrengthText(value):
            return '%.1f x' % float(value)

        @staticmethod
        def MillisecondsText(value):
            return '%d ms' % int(round(value))

        @staticmethod
        def SecondsText(value):
            return '%.1f s' % (float(value) / 1000.0)

        @staticmethod
        def IntegerText(value):
            return str(int(round(value)))

        def StyleCallback(self, key):
            def choose(*args):
                if not self._loading and not self._saving:
                    self._draft['depletionStyle'] = key
                    self.RefreshControls()
            return choose

        def CheckboxCallback(self, key):
            def changed(control, *args):
                if not self._loading and not self._saving:
                    self._draft[key] = bool(control.GetValue())
                    self.RefreshControls()
            return changed

        def SliderCallback(self, key, formatter, integer):
            def changed(control, *args):
                if not self._loading and not self._saving:
                    value = control.GetValue()
                    self._draft[key] = int(round(value)) if integer else round(float(value), 1)
                    self._readouts[key].text = formatter(self._draft[key])
                    self.RefreshControls()
            return changed

        def RefreshControls(self):
            style = self._draft['depletionStyle']
            for key, text, description in styles:
                selected = key == style
                state = C.UI_DISABLED if selected else C.UI_HIDDEN
                self._styleLines[key].state = state
                self._styleTints[key].state = state
                if selected:
                    self.styleDescription.text = description
            dust = self._draft['dustEnabled'] or style in ('dust', 'hybrid')
            enabled = {'dustIntensity': dust, 'dustLifetimeMs': dust,
                       'dustMaxConcurrent': dust,
                       'resizeDurationMs': self._draft['smoothShrink'],
                       'depletionDurationMs': style in ('dust', 'quiet')}
            for key, control in self._sliders.items():
                usable = enabled.get(key, True) and not self._saving
                (control.Enable if usable else control.Disable)()
                self._readouts[key].opacity = 1.0 if usable else 0.4
            for control in self._checks.values():
                (control.Disable if self._saving else control.Enable)()
            for control in self._styleButtons.values():
                control.enabled = not self._saving
            dirty = self._draft != self._snapshot
            usable = self.CanApply()
            self.applyButton.enabled = bool(dirty and usable and not self._saving)
            self.saveState.text = ('Unsaved changes' if dirty else 'No changes') if usable else 'Reconnect to apply changes'
            self.saveState.color = amber if dirty else muted

        def CanApply(self):
            # Native UI callbacks may already be queued when a session change
            # closes the window. An old draft must never enter another pilot's
            # settings, including when the session changes before our notify.
            return (not self.destroyed and owner.current() and owner.usable()
                    and owner.character_generation == self._characterGeneration
                    and owner.preferences.storage()[0] == self._characterID)

        def ApplyDraft(self, *args):
            if self.destroyed or self._saving or self._draft == self._snapshot:
                return
            if not self.CanApply():
                self.RefreshControls()
                return
            self._saving = True
            self.RefreshControls()
            try:
                owner.save_preferences(dict(self._draft))
                self._snapshot = self.ReadSnapshot()
                self._draft = dict(self._snapshot)
                self.RefreshControls()
                self.saveState.text = 'Preferences saved'
                self.saveState.color = teal
            except Exception as error:
                owner.diagnostic('PREFERENCES_SAVE_FAILED:%s' % type(error).__name__)
                self.saveState.text = 'Could not save. Changes are still here; try Apply again.'
                self.saveState.color = amber
            finally:
                self._saving = False
                self.applyButton.enabled = bool(self._draft != self._snapshot
                    and self.CanApply())
                for control in self._checks.values():
                    control.Enable()
                for control in self._styleButtons.values():
                    control.enabled = True
                # Restore disabled sliders after a completed or failed save.
                style = self._draft['depletionStyle']
                dust = self._draft['dustEnabled'] or style in ('dust', 'hybrid')
                for key, enabled in (('dustIntensity', dust), ('dustLifetimeMs', dust),
                    ('dustMaxConcurrent', dust), ('resizeDurationMs', self._draft['smoothShrink']),
                    ('depletionDurationMs', style in ('dust', 'quiet'))):
                    control = self._sliders[key]
                    (control.Enable if enabled else control.Disable)()
                    self._readouts[key].opacity = 1.0 if enabled else 0.4

        def Close(self, *args, **kwargs):
            if getattr(owner, 'window', None) is self:
                owner.window = None
            return Window.Close(self, *args, **kwargs)

    return AsteroidErosionWindow
