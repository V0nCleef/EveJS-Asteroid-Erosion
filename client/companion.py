# coding: utf-8
"""Asteroid presentation only. Native mining, targeting and removal still run."""
import __builtin__ as _ae_builtins
import blue as _ae_blue
import uthread as _ae_uthread
import random as _ae_random


class _AsteroidErosion(object):
    __notifyevents__ = ['OnDisconnect', 'OnConnectionClosed', 'OnSessionChanged']

    def __init__(self, config):
        self.config = config
        self.active = True
        self.hooks = []
        self.registered = []
        self.sm = None
        self.dust = {}
        self.anchors = {}
        self.dust_failed = False
        self.diagnostic_count = 0
        self.dust_reported = False
        self.dust_samples = 0
        self.preferences = _AEPreferences(config)
        self.window = None
        self.window_class = None
        self.character_generation = 0

    def settings_snapshot(self):
        self.preferences.base = self.config
        return self.preferences.snapshot()

    def save_preferences(self, values):
        result = self.preferences.save(values)
        self.diagnostic('PREFERENCES_SAVED')
        return result

    def usable(self):
        return self.current() and bool(self.hooks) and self.preferences.storage()[0] is not None

    def open_window(self):
        if not self.usable():
            return
        if self.window_class is None:
            self.window_class = _ae_make_window(self)
        self.window = self.window_class.Open(owner=self)

    def close_window(self):
        window, self.window = self.window, None
        if window is not None and not getattr(window, 'destroyed', False):
            window.Close()

    def current(self):
        return self.active and getattr(_ae_builtins, '_evejs_asteroid_erosion_v1', None) is self

    def diagnostic(self, text):
        print('ASTEROID_EROSION:' + text)
        # /noconsole hides print output. Keep a small, per-profile graphics log
        # containing only our status/errors, not login or session data.
        if self.diagnostic_count >= 64:
            return
        self.diagnostic_count += 1
        try:
            import time
            path = _ae_blue.paths.ResolvePath(u'cache:/asteroid-erosion.log')
            with open(path, 'a') as output:
                output.write(time.strftime('%Y-%m-%dT%H:%M:%SZ ', time.gmtime())
                             + 'ASTEROID_EROSION:' + str(text)[:400] + '\n')
        except Exception:
            pass

    def clear_dust(self, record):
        if self.dust.get(record['id']) is record:
            self.dust.pop(record['id'], None)
        root = record.get('root')
        scene = record.get('scene')
        if root is not None:
            try:
                if scene is not None:
                    scene.objects.fremove(root)
                root.translationCurve = None
                root.modelTranslationCurve = None
                del root.effectChildren[:]
            except Exception:
                pass

    def anchor_finish(self, park, ball):
        # NONE removes the original Destiny ball immediately. Native explosion
        # effects use a separate client-side ball to retain a valid position
        # through that removal and subsequent origin rebasing.
        model = getattr(ball, 'model', None)
        if model is None:
            return None
        position = tuple(float(value) for value in (ball.x, ball.y, ball.z))
        if any(not (-1.0e30 < value < 1.0e30) for value in position):
            raise ValueError('Asteroid position is unavailable')
        curve = park.AddClientSideBall(position)
        try:
            if curve is None or curve.id >= 0:
                raise RuntimeError('Native client-side anchor unavailable')
            model.translationCurve = curve
        except Exception:
            if curve is not None:
                park.RemoveClientSideBall(curve.id)
            raise
        record = dict(id=ball.id, park=park, curve=curve, model=model, ball=ball,
                      retiring=False)
        self.anchors[ball.id] = record
        return record

    def clear_anchor(self, record):
        if self.anchors.get(record['id']) is not record:
            return
        self.anchors.pop(record['id'], None)
        try:
            # Always remove from the owning park, even after a grid change.
            record['park'].RemoveClientSideBall(record['curve'].id)
        except Exception:
            self.diagnostic('ANCHOR_CLEANUP_FAILED')

    def retire_anchor(self, ball, config):
        record = self.anchors.get(ball.id)
        if record is None or record['retiring']:
            return
        record['retiring'] = True

        def retire():
            try:
                deadline = _ae_blue.os.GetSimTime() + int((config['dustLifetimeMs'] + 1000) * 10000)
                while self.current() and self.anchors.get(ball.id) is record:
                    model_done = (getattr(ball, 'model', None) is not record['model']
                                  or getattr(record['model'], 'translationCurve', None) is not record['curve'])
                    if model_done and ball.id not in self.dust:
                        return
                    if _ae_blue.os.GetSimTime() >= deadline:
                        dust = self.dust.get(ball.id)
                        if dust is not None:
                            self.clear_dust(dust)
                        return
                    _ae_blue.pyos.synchro.SleepSim(50)
            finally:
                self.clear_anchor(record)
        try:
            _ae_uthread.new(retire)
        except Exception:
            self.clear_anchor(record)

    def visual_radius(self, model, scale):
        # Match native ShipEffect's SCALE_RADIUS: modelScale is a nominal
        # asteroid size, not necessarily the rendered mesh's bounding radius.
        try:
            radius = float(model.GetBoundingSphereRadius())
            if 0.0 < radius < 1.0e12:
                return radius
        except Exception:
            pass
        return max(0.05, float(scale))

    def freeze_dust_center(self, record, ball):
        # Native Release clears the model's position curves. Keep the lingering
        # cloud at its last center without retaining a now-unpositioned model.
        root = record['root']
        if record.get('frozen'):
            return
        try:
            import trinity
            stamp = _ae_blue.os.GetSimTime()
            anchor = self.anchors.get(ball.id)
            position_curve = anchor['curve'] if anchor is not None else ball.GetPositionCurve()
            center = root.translationCurve.GetVectorAt(stamp)
            position = position_curve.GetVectorAt(stamp)
            offset = trinity.Tr2TranslationAdapter()
            offset.value = (center.x - position.x, center.y - position.y,
                            center.z - position.z)
            root.modelTranslationCurve = offset
            root.translationCurve = position_curve
            record['frozen'] = True
        except Exception as error:
            self.diagnostic('DUST_CENTER_FREEZE_FAILED:%s:%s'
                            % (type(error).__name__, str(error)[:120]))
            self.clear_dust(record)

    def plume_layout(self, ball_id, burst):
        # Private, repeatable RNG for a given rock and observed burst count,
        # without reseeding EVE's or another mod's random-number stream.
        rng = _ae_random.Random(int(ball_id) + burst * 2654435761)
        patches = []
        # Overlapping latitude bands and all four azimuth quadrants cover the
        # entire rock. Shuffle the visits so successive puffs reach other faces.
        for low, high in ((0.0, 75.0), (45.0, 135.0), (105.0, 180.0)):
            for quadrant in range(4):
                patches.append((max(0.0, low - rng.uniform(0.0, 8.0)),
                                min(180.0, high + rng.uniform(0.0, 8.0)),
                                max(0.0, quadrant * 90.0 - rng.uniform(8.0, 18.0)),
                                min(360.0, (quadrant + 1) * 90.0 + rng.uniform(8.0, 18.0)),
                                rng.uniform(0.90, 1.10), rng.uniform(0.75, 1.0),
                                rng.uniform(0.85, 1.15), rng.uniform(0.88, 0.98)))
        rng.shuffle(patches)
        return patches

    def size_dust(self, record, radius, step=0):
        # World-unit emitter dimensions, rather than scaling the whole cloud:
        # particles already shed keep drifting as the surface recedes.
        radius = max(0.05, float(radius) * record['visual_ratio'])
        # Advance once per animation step rather than sampling a clock cycle:
        # long configured resizes must not alias back to the same few regions.
        patch = record['plumes'][step % len(record['plumes'])]
        for shape in record['shapes']:
            # Overlap the visible bounds instead of a detached exterior ring.
            shape.minRadius = radius * 0.72
            shape.maxRadius = radius * patch[7]
            shape.minPhi, shape.maxPhi = patch[0], patch[1]
            shape.minTheta, shape.maxTheta = patch[2], patch[3]
            shape.minSpeed = radius * 0.035 * patch[5]
            shape.maxSpeed = radius * 0.09 * patch[5]
        for size in record['sizes']:
            size.minRange = (radius * 0.70 * patch[4], radius * 0.65 * patch[4], 0.0, 0.0)
            size.maxRange = (radius * 1.15 * patch[4], radius * 0.85 * patch[4], 0.0, 0.0)
        for emitter in record['emitters']:
            emitter.rate = record['base_rate'] * patch[6]
        record['radius'] = radius

    def sample_dust(self, record):
        # Native Blue properties, sampled during emission rather than treating
        # scene insertion as proof of rendering. Some builds do not expose the
        # geometry instance count to Python; report that explicitly.
        if self.dust_samples >= 8:
            return
        self.dust_samples += 1
        try:
            systems = record['systems']
            valid = ','.join(str(int(system.isValid)) for system in systems)
            bound = ','.join(str(getattr(item, 'isValid', 'unavailable'))
                             for item in record['emitters'])
            counts = []
            for system in systems:
                getter = getattr(system, 'GetInstanceCount', None)
                counts.append(str(getter()) if callable(getter) else 'unavailable')
            self.diagnostic('DUST_STATE:radius=%.3f:system=%s:emitter=%s:instances=%s:rate=%.1f'
                            % (record['radius'], valid, bound, ','.join(counts),
                               sum(item.rate for item in record['emitters'])))
        except Exception as error:
            self.diagnostic('DUST_STATE_UNAVAILABLE:%s:%s' % (type(error).__name__, str(error)[:120]))

    def begin_dust(self, ball, start, target, duration, config=None):
        config = dict(config or self.settings_snapshot())
        if (not config['dustEnabled'] or config['dustIntensity'] <= 0
                or self.dust_failed or target >= start or duration <= 0):
            return None
        visual_radius = self.visual_radius(ball.model, start)
        record = self.dust.get(ball.id)
        expire = None
        if record is not None and record.get('model') is not ball.model:
            self.clear_dust(record)
            record = None
        if record is None:
            if len(self.dust) >= config['dustMaxConcurrent']:
                return None
            record = {'id': ball.id, 'model': ball.model, 'root': None, 'scene': None,
                      'visual_ratio': visual_radius / start, 'burst': 0,
                      'plumes': self.plume_layout(ball.id, 0), 'base_rate': 0.0}
            self.dust[ball.id] = record
            stage = 'scene'
            try:
                scene = ball.spaceMgr.GetScene()
                if scene is None or not self.current():
                    self.clear_dust(record)
                    return None
                import trinity
                stage = 'resource'
                # Shipped lit asteroid dust; no client assets are copied or edited.
                effect = trinity.Load('res:/dx9/model/celestial/environment/rock/asteroidset_02/large/single/as2_l_01/effects/as2_l_01_dust_v2.black')
                shapes = list(effect.Find('trinity.Tr2SphereShapeAttributeGenerator'))
                generators = list(effect.Find('trinity.Tr2RandomUniformAttributeGenerator'))
                sizes = [item for item in generators if item.customName == 'size']
                lifetimes = [item for item in generators if item.elementType == 0]
                emitters = list(effect.Find('trinity.Tr2DynamicEmitter'))
                systems = list(effect.Find('trinity.Tr2ParticleSystem'))
                meshes = list(effect.Find('trinity.Tr2InstancedMesh'))
                stage = 'layout'
                if not (shapes and sizes and lifetimes and emitters and systems and meshes):
                    raise RuntimeError('Asteroid dust resource layout changed')
                # The source is a huge, continuous environment cloud. Replace
                # its dimensions/lifetimes, and remove its distance-display driver.
                for curve in list(effect.curveSets):
                    curve.Stop()
                    effect.curveSets.remove(curve)
                for child in effect.Find('trinity.EveChildParticleSystem'):
                    child.display = True
                for area in effect.Find('trinity.Tr2MeshArea'):
                    area.display = True
                seconds = config['dustLifetimeMs'] / 1000.0
                stage = 'lifetime'
                for item in lifetimes:
                    item.minRange = (0.0, seconds * 0.65, 0.0, 0.0)
                    item.maxRange = (0.0, seconds, 0.0, 0.0)
                stage = 'particle-buffers'
                for system in systems:
                    system.maxParticleCount = 384
                    # Match the installed client's particle editor Link():
                    # rebuild buffers first, then bind generators to them.
                    system.UpdateElementDeclaration()
                    if not system.isValid:
                        raise RuntimeError('Native dust particle system is invalid')
                stage = 'emitter-bind'
                for emitter in emitters:
                    emitter.Rebind()
                    if not getattr(emitter, 'isValid', True):
                        raise RuntimeError('Native dust emitter is invalid')
                stage = 'material'
                for parameter in effect.Find('trinity.Tr2FloatParameter'):
                    if parameter.name == 'Brightness':
                        parameter.value = 0.8
                for material in effect.Find('trinity.Tr2Effect'):
                    for index, pair in enumerate(material.constParameters):
                        if pair[0] == 'ParticleParams':
                            # Native shader: saturate((viewDepth-near)/(far-near)).
                            # Its original 250 m fade hides close surface puffs.
                            value = pair[1]
                            material.constParameters[index] = (
                                pair[0], (0.0, max(0.01, visual_radius * 0.01), value[2], value[3]))
                            material.RebuildCachedData()
                stage = 'mesh-bounds'
                extent = max(0.1, visual_radius * max(2.5, 1.92 + 0.09 * seconds))
                for mesh in meshes:
                    mesh.minBounds = (-extent, -extent, -extent)
                    mesh.maxBounds = (extent, extent, extent)
                stage = 'attach'
                root = trinity.EveEffectRoot2()
                root.name = 'AsteroidErosionDust'
                root.scaling = (1.0, 1.0, 1.0)
                # Use the same center-bounds curve as native model-bound FX.
                center = trinity.EveLocalPositionCurve(trinity.EveLocalPositionBehavior.centerBounds)
                center.parent = ball.model
                root.translationCurve = center
                root.effectChildren.append(effect)
                if not self.current():
                    self.clear_dust(record)
                    return None
                record.update(root=root, scene=scene, shapes=shapes, sizes=sizes,
                              emitters=emitters, systems=systems, until=0, finished=False)
                self.size_dust(record, start)
                # Begin at the current surface even on a final large mining cycle.
                scene.objects.append(root)

                def expire():
                    try:
                        while self.current() and self.dust.get(ball.id) is record:
                            if _ae_blue.os.GetSimTime() >= record['until']:
                                for emitter in emitters:
                                    emitter.rate = 0.0
                                record['finished'] = True
                                _ae_blue.pyos.synchro.SleepSim(int(record['lifetime']))
                                if record['finished']:
                                    return
                            else:
                                _ae_blue.pyos.synchro.SleepSim(50)
                    finally:
                        self.clear_dust(record)

            except Exception as error:
                self.clear_dust(record)
                self.dust_failed = True
                self.diagnostic('DUST_UNAVAILABLE:%s:%s:%s' % (stage, type(error).__name__, str(error)[:200]))
                return None
        if not record.get('root'):
            return None
        fraction = 1.0 - max(0.0, target / start) ** 3
        strength = min(1.0, max(0.15, fraction ** 0.5 * 4.0))
        # A reused emitter needs its current lifetime and bounds refreshed too.
        seconds = config['dustLifetimeMs'] / 1000.0
        effect = record['root'].effectChildren[0]
        for item in effect.Find('trinity.Tr2RandomUniformAttributeGenerator'):
            if item.elementType == 0:
                item.minRange = (0.0, seconds * 0.65, 0.0, 0.0)
                item.maxRange = (0.0, seconds, 0.0, 0.0)
        extent = max(0.1, visual_radius * max(2.5, 1.92 + 0.09 * seconds))
        for mesh in effect.Find('trinity.Tr2InstancedMesh'):
            mesh.minBounds = (-extent, -extent, -extent)
            mesh.maxBounds = (extent, extent, extent)
        record['lifetime'] = config['dustLifetimeMs']
        record['base_rate'] = (420.0 + 220.0 * strength) * config['dustIntensity']
        record['finished'] = False
        record['until'] = _ae_blue.os.GetSimTime() + int(duration * 10000)
        record['visual_ratio'] = visual_radius / start
        record['plumes'] = self.plume_layout(ball.id, record['burst'])
        record['burst'] += 1
        self.size_dust(record, start)
        # All emission state must exist before a new task can inspect it.
        if expire is not None:
            _ae_uthread.new(expire)
        if not self.dust_reported:
            self.dust_reported = True
            self.diagnostic('DUST_READY:scale=%.3f:radius=%.3f:particles=384:brightness=0.8:plumes=12:center=model'
                            % (start, visual_radius))
        return record

    def animate(self, ball, target, duration, completion=None, config=None):
        config = dict(config or self.settings_snapshot())
        character_generation = self.character_generation
        model = getattr(ball, 'model', None)
        generation = getattr(ball, '_ae_resize_generation', 0) + 1
        ball._ae_resize_generation = generation
        if model is None or getattr(ball, 'released', False):
            if completion is not None:
                completion()
            return
        start_scale = float(model.modelScale)

        def run():
            dust = None
            try:
                if (not self.current() or self.character_generation != character_generation
                        or getattr(ball, '_ae_resize_generation', 0) != generation):
                    return
                # An optional particle failure must never interrupt the resize.
                try:
                    # Zero-time visual resizing still emits a short surface puff.
                    dust = self.begin_dust(ball, start_scale, target, max(150, duration), config=config)
                    if dust is not None and duration <= 0 and completion is not None:
                        self.freeze_dust_center(dust, ball)
                except Exception:
                    self.diagnostic('DUST_FAILED')
                started = _ae_blue.os.GetSimTime()
                sampled = False
                # A task exists only during a resize, with a bounded number of
                # steps. Simulation sleeps respect pause and time dilation.
                steps = max(1, min(60, int(duration / 25.0) + 1))
                for step in range(steps + 1):
                    if (not self.current() or self.character_generation != character_generation
                            or getattr(ball, 'released', False)
                            or getattr(ball, 'model', None) is not model
                            or getattr(ball, '_ae_resize_generation', 0) != generation):
                        return
                    elapsed = (_ae_blue.os.GetSimTime() - started) / 10000.0
                    if dust is not None and not sampled and elapsed >= min(150, duration * 0.5):
                        sampled = True
                        self.sample_dust(dust)
                    amount = 1.0 if duration <= 0 else min(1.0, max(0.0, elapsed / duration))
                    smooth = amount * amount * (3.0 - 2.0 * amount)
                    model.modelScale = start_scale + (target - start_scale) * smooth
                    if dust is not None and duration > 0:
                        try:
                            self.size_dust(dust, model.modelScale, step)
                        except Exception as error:
                            self.clear_dust(dust)
                            dust = None
                            self.diagnostic('DUST_SIZE_FAILED:%s:%s' % (type(error).__name__, str(error)[:200]))
                    if amount >= 1.0:
                        break
                    _ae_blue.pyos.synchro.SleepSim(int(max(1, duration / steps)))
                if (self.current() and getattr(ball, 'model', None) is model
                        and getattr(ball, '_ae_resize_generation', 0) == generation):
                    model.modelScale = target
            except Exception:
                self.diagnostic('ANIMATION_FAILED')
            finally:
                try:
                    if dust is not None and getattr(ball, '_ae_resize_generation', 0) == generation:
                        if duration > 0:
                            for emitter in dust['emitters']:
                                emitter.rate = 0.0
                            dust['until'] = _ae_blue.os.GetSimTime()
                        if completion is not None:
                            self.freeze_dust_center(dust, ball)
                except Exception:
                    self.diagnostic('DUST_CLEANUP_FAILED')
                finally:
                    if completion is not None:
                        completion()

        try:
            _ae_uthread.new(run)
        except Exception:
            if completion is not None:
                completion()

    def patch(self, owner, name, make_wrapper):
        original = getattr(owner, name)
        wrapper = make_wrapper(original)
        setattr(owner, name, wrapper)
        self.hooks.append((owner, name, original, wrapper))

    def install(self, Park, Asteroid):
        manager = self
        from evetypes import GetGroupID
        from inventorycommon.const import groupIce

        def ore_asteroid(ball):
            return (isinstance(ball, Asteroid)
                    and GetGroupID(ball.typeData.get('typeID')) != groupIce)

        def resize_hook(original):
            def flush(park, state):
                result = original(park, state)
                if manager.current():
                    try:
                        for stamp, event in state:
                            name, args = event
                            if name != 'SetBallRadius' or len(args) != 2:
                                continue
                            ball = park.balls.get(args[0])
                            if ore_asteroid(ball) and not getattr(ball, '_ae_depleting', False):
                                # Read the applied native radius, not a possibly
                                # rejected or future packet's requested value.
                                config = manager.settings_snapshot()
                                manager.animate(ball, float(ball.radius),
                                                config['resizeDurationMs'] if config['smoothShrink'] else 0,
                                                config=config)
                    except Exception:
                        manager.diagnostic('RESIZE_FAILED')
                return result
            return flush

        def destruction_hook(original):
            def set_effect(park, ball_id, effect):
                result = original(park, ball_id, effect)
                if manager.current() and effect == 2:  # Native DISSOLVE / mining depletion.
                    try:
                        ball = park.balls.get(ball_id)
                        if ore_asteroid(ball):
                            if getattr(ball, '_ae_depleting', False):
                                ball.destructionEffectId = (2 if ball._ae_finish_config['depletionStyle'] in ('burn', 'hybrid') else 0)
                                return result
                            config = manager.settings_snapshot()
                            if config['depletionStyle'] in ('dust', 'quiet'):
                                if manager.anchor_finish(park, ball) is None:
                                    return result
                            ball._ae_finish_config = config
                            ball._ae_depleting = True
                            ball._ae_resize_generation = getattr(ball, '_ae_resize_generation', 0) + 1
                            if ball._ae_finish_config['depletionStyle'] not in ('burn', 'hybrid'):
                                ball.destructionEffectId = 0  # Quiet modes override auto-explosion.
                    except Exception:
                        manager.diagnostic('DEPLETION_EFFECT_FAILED')
                return result
            return set_effect

        def release_hook(original):
            def release(ball, origin=None):
                if (not manager.current() or not getattr(ball, '_ae_depleting', False)
                        or getattr(ball, 'model', None) is None or getattr(ball, 'released', False)):
                    record = manager.dust.get(ball.id)
                    if record is not None:
                        manager.clear_dust(record)
                    return original(ball, origin)
                if getattr(ball, '_ae_release_pending', False):
                    return None
                ball._ae_release_pending = True
                config = dict(ball._ae_finish_config)
                mode = config['depletionStyle']
                config['dustEnabled'] = mode in ('dust', 'hybrid')
                if mode in ('burn', 'hybrid'):
                    try:
                        record = manager.dust.get(ball.id)
                        if record is not None:
                            manager.clear_dust(record)
                        if mode == 'hybrid':
                            manager.burn_dust(ball, config)
                    except Exception:
                        manager.diagnostic('BURN_DUST_FAILED')
                    # Native DISSOLVE owns its 33-second animation and delay.
                    return original(ball, origin)
                released_native = [False]
                def finish():
                    if not released_native[0]:
                        released_native[0] = True
                        try:
                            return original(ball, origin)
                        finally:
                            manager.retire_anchor(ball, config)
                try:
                    target = min(float(ball.model.modelScale), max(0.05, float(ball.model.modelScale) * 0.005))
                    manager.animate(ball, target, config['depletionDurationMs'],
                                    completion=finish, config=config)
                except Exception:
                    return finish()
                return None
            return release

        self.patch(Park, 'RealFlushState', resize_hook)
        self.patch(Park, 'SetDestructionEffectOnRemove', destruction_hook)
        self.patch(Asteroid, 'Release', release_hook)
        self.diagnostic('READY:0.2.0')

    def burn_dust(self, ball, config):
        # A brief independent puff; never rescale or delay the native burn.
        start = float(ball.model.modelScale)
        duration = max(150, config['depletionDurationMs'])
        record = self.begin_dust(ball, start, start * 0.995, duration, config=config)
        if record is None:
            return
        self.freeze_dust_center(record, ball)

        def emit():
            try:
                steps = max(1, min(60, int(duration / 25.0)))
                for step in range(steps):
                    if not self.current() or self.dust.get(ball.id) is not record:
                        return
                    self.size_dust(record, start, step)
                    _ae_blue.pyos.synchro.SleepSim(max(1, int(duration / steps)))
            finally:
                if self.dust.get(ball.id) is record:
                    for emitter in record['emitters']:
                        emitter.rate = 0.0
                    record['until'] = _ae_blue.os.GetSimTime()
        _ae_uthread.new(emit)

    def start(self):
        try:
            for attempt in range(240):
                if not self.current():
                    return
                context = globals().get('_ae_context') or {}
                self.sm = context.get('sm') or getattr(_ae_builtins, 'sm', None)
                if self.sm is not None:
                    break
                _ae_blue.pyos.synchro.SleepWallclock(500)
            else:
                self.close()
                self.diagnostic('SERVICE_TIMEOUT')
                return
            from eve.client.script.remote.michelle import Park
            from eve.client.script.environment.spaceObject.asteroid import Asteroid
            self.install(Park, Asteroid)
            for event in self.__notifyevents__:
                self.sm.RegisterForNotifyEvent(self, event)
                self.registered.append(event)
        except Exception:
            self.close()
            self.diagnostic('INSTALL_FAILED')

    def OnDisconnect(self, *args):
        self.close()

    def OnConnectionClosed(self, *args):
        self.close()

    def OnSessionChanged(self, isRemote, session, changes):
        if 'charid' in changes:
            self.character_generation += 1
            self.close_window()
            self.preferences.reset_session()
            for record in list(self.dust.values()):
                self.clear_dust(record)
            for record in list(self.anchors.values()):
                self.clear_anchor(record)

    def close(self):
        self.active = False
        self.close_window()
        for record in list(self.dust.values()):
            self.clear_dust(record)
        for record in list(self.anchors.values()):
            self.clear_anchor(record)
        # Restore only hooks still owned by this instance. Later wrappers from
        # another mod remain intact; our retained wrapper becomes a pass-through.
        for owner, name, original, wrapper in reversed(self.hooks):
            current = getattr(owner, name, None)
            # Python 2 exposes an unbound method descriptor when reading a
            # function from a class; compare the underlying function identity.
            function = getattr(current, 'im_func', getattr(current, '__func__', current))
            if function is wrapper:
                setattr(owner, name, original)
        self.hooks = []
        if self.sm is not None:
            for event in self.registered:
                try:
                    self.sm.UnregisterForNotifyEvent(self, event)
                except Exception:
                    pass
        self.registered = []


_ae_previous = getattr(_ae_builtins, '_evejs_asteroid_erosion_v1', None)
if _ae_previous is not None:
    _ae_previous.close()
_ae_manager = _AsteroidErosion(_ae_config)
_ae_builtins._evejs_asteroid_erosion_v1 = _ae_manager
_ae_uthread.new(_ae_manager.start)
