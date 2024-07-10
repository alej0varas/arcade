"""
The main window class that all object-oriented applications should
derive from.
"""

from __future__ import annotations

import logging
import os
import time
from typing import TYPE_CHECKING, Optional

import pyglet
import pyglet.gl as gl
import pyglet.window.mouse
from pyglet.display.base import ScreenMode
from pyglet.window import MouseCursor

import arcade
from arcade.clock import Clock, FixedClock
from arcade.color import TRANSPARENT_BLACK
from arcade.context import ArcadeContext
from arcade.sections import SectionManager
from arcade.types import LBWH, Color, Rect, RGBANormalized, RGBOrA255
from arcade.utils import is_raspberry_pi
from arcade.window_commands import get_display_size, set_window

if TYPE_CHECKING:
    from arcade.start_finish_data import StartFinishRenderData


LOG = logging.getLogger(__name__)

MOUSE_BUTTON_LEFT = 1
MOUSE_BUTTON_MIDDLE = 2
MOUSE_BUTTON_RIGHT = 4

_window: "Window"

__all__ = [
    "get_screens",
    "NoOpenGLException",
    "Window",
    "open_window",
    "View",
    "MOUSE_BUTTON_LEFT",
    "MOUSE_BUTTON_MIDDLE",
    "MOUSE_BUTTON_RIGHT",
]


def get_screens() -> list:
    """
    Return a list of screens. So for a two-monitor setup, this should return
    a list of two screens. Can be used with arcade.Window to select which
    window we full-screen on.

    :returns: List of screens, one for each monitor.
    """
    display = pyglet.display.get_display()
    return display.get_screens()


class NoOpenGLException(Exception):
    """
    Exception when we can't get an OpenGL 3.3+ context
    """

    pass


class Window(pyglet.window.Window):
    """
    The Window class forms the basis of most advanced games that use Arcade.
    It represents a window on the screen, and manages events.

    .. _pyglet_pg_window_size_position: https://pyglet.readthedocs.io/en/latest/programming_guide/windowing.html#size-and-position
    .. _pyglet_pg_window_style: https://pyglet.readthedocs.io/en/latest/programming_guide/windowing.html#window-style

    :param width: Window width
    :param height: Window height
    :param title: Title (appears in title bar)
    :param fullscreen: Should this be full screen?
    :param resizable: Can the user resize the window?
    :param update_rate: How frequently to run the on_update event.
    :param draw_rate: How frequently to run the on_draw event. (this is the FPS limit)
    :param fixed_rate: How frequently should the fixed_updates run, fixed updates will always run at this rate.
    :param fixed_frame_cap: The maximum number of fixed updates that can occur in one update loop.
                                defaults to infinite. If large lag spikes cause your game to freeze, try setting
                                this to a smaller number. This may cause your physics to lag behind temporarily
    :param antialiasing: Should OpenGL's anti-aliasing be enabled?
    :param gl_version: What OpenGL version to request. This is ``(3, 3)`` by default \
                                       and can be overridden when using more advanced OpenGL features.
    :param screen: Pass a pyglet :py:class:`~pyglet.display.Screen` to
        request the window be placed on it. See `pyglet's window size &
        position guide <pyglet_pg_window_size_position_>`_ to learn more.
    :param style: Request a non-default window style, such as borderless.
        Some styles only work in certain situations. See `pyglet's guide
        to window style <pyglet_pg_window_style_>`_ to learn more.
    :param visible: Should the window be visible immediately
    :param vsync: Wait for vertical screen refresh before swapping buffer \
                       This can make animations and movement look smoother.
    :param gc_mode: Decides how OpenGL objects should be garbage collected ("context_gc" (default) or "auto")
    :param center_window: If true, will center the window.
    :param samples: Number of samples used in antialiasing (default 4). \
                         Usually this is 2, 4, 8 or 16.
    :param enable_polling: Enabled input polling capability. This makes the ``keyboard`` and ``mouse`` \
                                attributes available for use.
    """

    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        title: Optional[str] = "Arcade Window",
        fullscreen: bool = False,
        resizable: bool = False,
        update_rate: float = 1 / 60,
        antialiasing: bool = True,
        gl_version: tuple[int, int] = (3, 3),
        screen: Optional[pyglet.display.Screen] = None,
        style: Optional[str] = pyglet.window.Window.WINDOW_STYLE_DEFAULT,
        visible: bool = True,
        vsync: bool = False,
        gc_mode: str = "context_gc",
        center_window: bool = False,
        samples: int = 4,
        enable_polling: bool = True,
        gl_api: str = "gl",
        draw_rate: float = 1 / 60,
        fixed_rate: float = 1.0 / 60.0,
        fixed_frame_cap: Optional[int] = None,
    ) -> None:
        # In certain environments we can't have antialiasing/MSAA enabled.
        # Detect replit environment
        if os.environ.get("REPL_ID"):
            antialiasing = False

        # Detect Raspberry Pi and switch to OpenGL ES 3.1
        if is_raspberry_pi():
            gl_version = 3, 1
            gl_api = "gles"

        #: Whether this is a headless window
        self.headless: bool = pyglet.options.get("headless") is True

        config = None
        # Attempt to make window with antialiasing
        if antialiasing:
            try:
                config = pyglet.gl.Config(
                    major_version=gl_version[0],
                    minor_version=gl_version[1],
                    opengl_api=gl_api,
                    double_buffer=True,
                    sample_buffers=1,
                    samples=samples,
                    depth_size=24,
                    stencil_size=8,
                    red_size=8,
                    green_size=8,
                    blue_size=8,
                    alpha_size=8,
                )
                display = pyglet.display.get_display()
                screen = display.get_default_screen()
                if screen:
                    config = screen.get_best_config(config)
            except pyglet.window.NoSuchConfigException:
                LOG.warning("Skipping antialiasing due missing hardware/driver support")
                config = None
                antialiasing = False
        # If we still don't have a config
        if not config:
            config = pyglet.gl.Config(
                major_version=gl_version[0],
                minor_version=gl_version[1],
                opengl_api=gl_api,
                double_buffer=True,
                depth_size=24,
                stencil_size=8,
                red_size=8,
                green_size=8,
                blue_size=8,
                alpha_size=8,
            )
        try:
            super().__init__(
                width=width,
                height=height,
                caption=title,
                resizable=resizable,
                config=config,
                vsync=vsync,
                visible=visible,
                style=style,
            )
            self.register_event_type("on_update")
            self.register_event_type("on_action")
            self.register_event_type("on_fixed_update")
        except pyglet.window.NoSuchConfigException:
            raise NoOpenGLException(
                "Unable to create an OpenGL 3.3+ context. "
                "Check to make sure your system supports OpenGL 3.3 or higher."
            )
        if antialiasing:
            try:
                gl.glEnable(gl.GL_MULTISAMPLE_ARB)
            except pyglet.gl.GLException:
                LOG.warning("Warning: Anti-aliasing not supported on this computer.")

        self._global_clock: Clock = Clock()
        self._fixed_clock: FixedClock = FixedClock(self._global_clock, fixed_rate)

        # We don't call the set_draw_rate function here because unlike the updates, the draw scheduling
        # is initially set in the call to pyglet.app.run() that is done by the run() function.
        # run() will pull this draw rate from the Window and use it. Calls to set_draw_rate only need
        # to be done if changing it after the application has been started.
        self._draw_rate = draw_rate

        # Fixed rate cannot be changed post initialisation as this throws off physics sims.
        # If more time resolution is needed in fixed updates, devs can do 'sub-stepping'.
        self._fixed_rate = fixed_rate
        self._fixed_frame_cap = fixed_frame_cap
        self.set_update_rate(update_rate)

        self.set_vsync(vsync)

        super().set_fullscreen(fullscreen, screen)
        # This used to be necessary on Linux, but no longer appears to be.
        # With Pyglet 2.0+, setting this to false will not allow the screen to
        # update. It does, however, cause flickering if creating a window that
        # isn't derived from the Window class.
        # self.invalid = False
        set_window(self)

        self.push_handlers(on_resize=self._on_resize)

        self._ctx: ArcadeContext = ArcadeContext(self, gc_mode=gc_mode, gl_api=gl_api)
        self._background_color: Color = TRANSPARENT_BLACK

        self._current_view: Optional[View] = None
        self.textbox_time = 0.0
        self.key: Optional[int] = None

        # See if we should center the window
        if center_window:
            self.center_window()

        if enable_polling:
            self.keyboard = pyglet.window.key.KeyStateHandler()

            if pyglet.options["headless"]:
                self.push_handlers(self.keyboard)

            else:
                self.mouse = pyglet.window.mouse.MouseStateHandler()
                self.push_handlers(self.keyboard, self.mouse)
        else:
            self.keyboard = None
            self.mouse = None

        # Framebuffer for drawing content into when start_render is called.
        # These are typically functions just at module level wrapped in
        # start_render and finish_render calls. The framebuffer is repeatedly
        # rendered to the window when the event loop starts.
        self._start_finish_render_data: Optional[StartFinishRenderData] = None

    @property
    def current_view(self) -> Optional["View"]:
        """
        This property returns the current view being shown.
        To set a different view, call the
        :py:meth:`arcade.Window.show_view` method.

        """
        return self._current_view

    @property
    def ctx(self) -> ArcadeContext:
        """
        The OpenGL context for this window.

        :type: :py:class:`arcade.ArcadeContext`
        """
        return self._ctx

    def clear(
        self,
        color: Optional[RGBOrA255] = None,
        color_normalized: Optional[RGBANormalized] = None,
        viewport: Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        """Clears the window with the configured background color
        set through :py:attr:`arcade.Window.background_color`.

        :param color: (Optional) override the current background color
            with one of the following:

            1. A :py:class:`~arcade.types.Color` instance
            2. A 3 or 4-length RGB/RGBA :py:class:`tuple` of byte values (0 to 255)

        :param color_normalized: (Optional) override the current background color
            using normalized values (0.0 to 1.0). For example, (1.0, 0.0, 0.0, 1.0)
            making the window contents red.

        :param Tuple[int, int, int, int] viewport: The viewport range to clear
        """
        # Use the configured background color if none is provided
        if color is None and color_normalized is None:
            color = self.background_color
        self.ctx.screen.clear(color=color, color_normalized=color_normalized, viewport=viewport)

    @property
    def background_color(self) -> Color:
        """
        Get or set the background color for this window.
        This affects what color the window will contain when
        :py:meth:`~arcade.Window.clear()` is called.

        Examples::

            # Use Arcade's built in Color values
            window.background_color = arcade.color.AMAZON

            # Set the background color with a custom Color instance
            MY_RED = arcade.types.Color(255, 0, 0)
            window.background_color = MY_RED

            # Set the background color directly from an RGBA tuple
            window.background_color = 255, 0, 0, 255

            # (Discouraged)
            # Set the background color directly from an RGB tuple
            # RGB tuples will assume 255 as the opacity / alpha value
            window.background_color = 255, 0, 0

        :type: Color
        """
        return self._background_color

    @background_color.setter
    def background_color(self, value: RGBOrA255) -> None:
        self._background_color = Color.from_iterable(value)

    @property
    def rect(self) -> Rect:
        """Return a Rect describing the size of the window."""
        return LBWH(0, 0, self.width, self.height)

    def run(self) -> None:
        """
        Run the main loop.
        After the window has been set up, and the event hooks are in place, this is usually one of the last
        commands on the main program. This is a blocking function starting pyglet's event loop
        meaning it will start to dispatch events such as ``on_draw`` and ``on_update``.
        """
        arcade.run()

    def close(self) -> None:
        """Close the Window."""
        super().close()
        # Make sure we don't reference the window any more
        set_window(None)
        pyglet.clock.unschedule(self._dispatch_updates)

    def set_fullscreen(
        self,
        fullscreen: bool = True,
        screen: Optional["Window"] = None,
        mode: Optional[ScreenMode] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> None:
        """
        Set if we are full screen or not.

        :param fullscreen:
        :param screen: Which screen should we display on? See :func:`get_screens`
        :param mode:
                The screen will be switched to the given mode.  The mode must
                have been obtained by enumerating `Screen.get_modes`.  If
                None, an appropriate mode will be selected from the given
                `width` and `height`.
        :param width:
        :param height:
        """
        super().set_fullscreen(fullscreen, screen, mode, width, height)

    def center_window(self) -> None:
        """
        Center the window on the screen.
        """
        # Get the display screen using pyglet
        screen_width, screen_height = get_display_size()

        window_width, window_height = self.get_size()
        # Center the window
        self.set_location((screen_width - window_width) // 2, (screen_height - window_height) // 2)

    def on_update(self, delta_time: float) -> Optional[bool]:
        """
        Move everything. Perform collision checks. Do all the game logic here.

        :param delta_time: Time interval since the last time the function was called.
        """
        pass

    def on_fixed_update(self, delta_time: float):
        """
        Move everything. Perform collision checks. Always

        """
        pass

    def _dispatch_updates(self, delta_time: float) -> None:
        """
        Internal function that is scheduled with Pyglet's clock, this function gets run by the clock, and
        dispatches the on_update events.
        It also accumulates time and runs fixed updates until the Fixed Clock catches up to the global clock
        """
        self._global_clock.tick(delta_time)
        fixed_count = 0
        while self._fixed_clock.accumulated >= self._fixed_rate and (
            self._fixed_frame_cap is None or fixed_count <= self._fixed_frame_cap
        ):
            self._fixed_clock.tick(self._fixed_rate)
            self.dispatch_event("on_fixed_update", self._fixed_rate)
            fixed_count += 1
        self.dispatch_event("on_update", delta_time)

    def set_update_rate(self, rate: float) -> None:
        """
        Set how often the on_update function should be dispatched.
        For example, self.set_update_rate(1 / 60) will set the update rate to 60 times per second.

        :param rate: Update frequency in seconds
        """
        self._update_rate = rate
        pyglet.clock.unschedule(self._dispatch_updates)
        pyglet.clock.schedule_interval(self._dispatch_updates, rate)

    def set_draw_rate(self, rate: float) -> None:
        """
        Set how often the on_draw function should be run.
        For example, set.set_draw_rate(1 / 60) will set the draw rate to 60 frames per second.
        """
        self._draw_rate = rate
        pyglet.clock.unschedule(pyglet.app.event_loop._redraw_windows)
        pyglet.clock.schedule_interval(pyglet.app.event_loop._redraw_windows, self._draw_rate)

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> Optional[bool]:
        """
        Called repeatedly while the mouse is moving over the window.

        Override this function to respond to changes in mouse position.

        :param x: x position of mouse within the window in pixels
        :param y: y position of mouse within the window in pixels
        :param dx: Change in x since the last time this method was called
        :param dy: Change in y since the last time this method was called
        """
        pass

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> Optional[bool]:
        """
        Called once whenever a mouse button gets pressed down.

        Override this function to handle mouse clicks. For an example of
        how to do this, see arcade's built-in :ref:`aiming and shooting
        bullets <sprite_bullets_aimed>` demo.

        .. seealso:: :meth:`~.Window.on_mouse_release`

        :param x: x position of the mouse
        :param y: y position of the mouse
        :param button: What button was pressed. This will always be
                           one of the following:

                           * ``arcade.MOUSE_BUTTON_LEFT``
                           * ``arcade.MOUSE_BUTTON_RIGHT``
                           * ``arcade.MOUSE_BUTTON_MIDDLE``

        :param modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        pass

    def on_mouse_drag(
        self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int
    ) -> Optional[bool]:
        """
        Called repeatedly while the mouse moves with a button down.

        Override this function to handle dragging.

        :param x: x position of mouse
        :param y: y position of mouse
        :param dx: Change in x since the last time this method was called
        :param dy: Change in y since the last time this method was called
        :param buttons: Which button is pressed
        :param modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        return self.on_mouse_motion(x, y, dx, dy)

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> Optional[bool]:
        """
        Called once whenever a mouse button gets released.

        Override this function to respond to mouse button releases. This
        may be useful when you want to use the duration of a mouse click
        to affect gameplay.

        :param x: x position of mouse
        :param y: y position of mouse
        :param button: What button was hit. One of:
                           arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT,
                           arcade.MOUSE_BUTTON_MIDDLE
        :param modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        return False

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> Optional[bool]:
        """
        Called repeatedly while a mouse scroll wheel moves.

        Override this function to respond to scroll events. The scroll
        arguments may be positive or negative to indicate direction, but
        the units are unstandardized. How many scroll steps you receive
        may vary wildly between computers depending a number of factors,
        including system settings and the input devices used (i.e. mouse
        scrollwheel, touchpad, etc).

        .. warning:: Not all users can scroll easily!

                     Only some input devices support horizontal
                     scrolling. Standard vertical scrolling is common,
                     but some laptop touchpads are hard to use.

                     This means you should be careful about how you use
                     scrolling. Consider making it optional
                     to maximize the number of people who can play your
                     game!

        :param x: x position of mouse
        :param y: y position of mouse
        :param scroll_x: number of steps scrolled horizontally
                             since the last call of this function
        :param scroll_y: number of steps scrolled vertically since
                             the last call of this function
        """
        return False

    def set_mouse_visible(self, visible: bool = True) -> None:
        """
        Set whether to show the system's cursor while over the window

        By default, the system mouse cursor is visible whenever the
        mouse is over the window. To hide the cursor, pass ``False`` to
        this function. Pass ``True`` to make the cursor visible again.

        The window will continue receiving mouse events while the cursor
        is hidden, including movements and clicks. This means that
        functions like :meth:`~.Window.on_mouse_motion` and
        t':meth:`~.Window.on_mouse_press` will continue to work normally.

        You can use this behavior to visually replace the system mouse
        cursor with whatever you want. One example is :ref:`a game
        character that is always at the most recent mouse position in
        the window<sprite_collect_coins>`.

        .. note:: Advanced users can try using system cursor state icons

                 It may be possible to use system icons representing
                 cursor interaction states such as hourglasses or resize
                 arrows by using features ``arcade.Window`` inherits
                 from the underlying pyglet window class. See the
                 `pyglet overview on cursors
                 <https://pyglet.readthedocs.io/en/master/programming_guide/mouse.html#changing-the-mouse-cursor>`_
                 for more information.

        :param visible: Whether to hide the system mouse cursor
        """
        super().set_mouse_visible(visible)

    def on_action(self, action_name: str, state) -> None:
        pass

    def on_key_press(self, symbol: int, modifiers: int) -> Optional[bool]:
        """
        Called once when a key gets pushed down.

        Override this function to add key press functionality.

        .. tip:: If you want the length of key presses to affect
                 gameplay, you also need to override
                 :meth:`~.Window.on_key_release`.

        :param symbol: Key that was just pushed down
        :param modifiers: Bitwise 'and' of all modifiers (shift,
                              ctrl, num lock) active during this event.
                              See :ref:`keyboard_modifiers`.
        """
        try:
            self.key = symbol
        except AttributeError:
            pass

        return False

    def on_key_release(self, symbol: int, modifiers: int) -> Optional[bool]:
        """
        Called once when a key gets released.

        Override this function to add key release functionality.

        Situations that require handling key releases include:

        * Rhythm games where a note must be held for a certain
          amount of time
        * 'Charging up' actions that change strength depending on
          how long a key was pressed
        * Showing which keys are currently pressed down

        :param symbol: Key that was just released
        :param modifiers: Bitwise 'and' of all modifiers (shift,
                              ctrl, num lock) active during this event.
                              See :ref:`keyboard_modifiers`.
        """
        try:
            self.key = None
        except AttributeError:
            pass

        return False

    def on_draw(self) -> Optional[bool]:
        """
        Override this function to add your custom drawing code.
        """
        if self._start_finish_render_data:
            self.clear()
            self._start_finish_render_data.draw()
            return True

        return False

    def _on_resize(self, width: int, height: int):
        """The internal method called when the window is resized.

        The purpose of this method is mainly setting the viewport
        to the new size of the window. Users should override
        :meth:`~arcade.Window.on_resize` instead. This method is
        called first.

        :param width: New width
        :param height: New height
        """

        # Retain viewport
        self.viewport = (0, 0, width, height)

        return False

    def on_resize(self, width: int, height: int) -> Optional[bool]:
        """
        Override this method to add custom actions when the window is resized.

        An internal ``_on_resize`` is called first adjusting the viewport
        to the new size of the window so there is no need to call
        ```super().on_resize(width, height)```.

        :param width: New width
        :param height: New height
        """
        pass

    def set_min_size(self, width: int, height: int) -> None:
        """Wrap the Pyglet window call to set minimum size

        :param width: width in pixels.
        :param height: height in pixels.
        """

        if self._resizable:
            super().set_minimum_size(width, height)
        else:
            raise ValueError("Cannot set min size on non-resizable window")

    def set_max_size(self, width: int, height: int) -> None:
        """Wrap the Pyglet window call to set maximum size

        :param width: width in pixels.
        :param height: height in pixels.
        :Raises ValueError:

        """

        if self._resizable:
            super().set_maximum_size(width, height)
        else:
            raise ValueError("Cannot set max size on non-resizable window")

    def set_size(self, width: int, height: int) -> None:
        """
        Ignore the resizable flag and set the size

        :param width:
        :param height:
        """

        super().set_size(width, height)

    def get_size(self) -> tuple[int, int]:
        """
        Get the size of the window.

        :returns: (width, height)
        """

        return super().get_size()

    def get_location(self) -> tuple[int, int]:
        """
        Return the X/Y coordinates of the window

        :returns: x, y of window location
        """

        return super().get_location()

    def set_visible(self, visible: bool = True):
        """
        Set if the window is visible or not. Normally, a program's window is visible.

        :param visible:
        """
        super().set_visible(visible)

    def use(self) -> None:
        """Bind the window's framebuffer for rendering commands"""
        self.ctx.screen.use()

    @property
    def default_camera(self):
        """
        Provides a reference to the default arcade camera.
        Automatically sets projection and view to the size
        of the screen.
        """
        return self._ctx._default_camera

    @property
    def current_camera(self):
        """
        Get/Set the current camera. This represents the projector
        currently being used to define the projection and view matrices.
        """
        return self._ctx.current_camera

    @current_camera.setter
    def current_camera(self, next_camera):
        self._ctx.current_camera = next_camera

    @property
    def viewport(self) -> tuple[int, int, int, int]:
        """
        Get/Set the viewport of the window. This is the viewport used for
        on-screen rendering. If the screen is in use it will also update the
        default camera.
        """
        return self._ctx.screen.viewport

    @viewport.setter
    def viewport(self, new_viewport: tuple[int, int, int, int]):
        if self._ctx.screen == self._ctx.active_framebuffer:
            self._ctx.viewport = new_viewport
        else:
            self._ctx.screen.viewport = new_viewport

    def test(self, frames: int = 10) -> None:
        """
        Used by unit test cases. Runs the event loop a few times and stops.

        :param frames:
        """
        start_time = time.time()
        for _ in range(frames):
            self.switch_to()
            self.dispatch_events()
            self.dispatch_event("on_draw")
            self.flip()
            current_time = time.time()
            elapsed_time = current_time - start_time
            start_time = current_time
            if elapsed_time < 1.0 / 60.0:
                sleep_time = (1.0 / 60.0) - elapsed_time
                time.sleep(sleep_time)
            self._dispatch_updates(1 / 60)

    def show_view(self, new_view: "View") -> None:
        """
        Select the view to show in the next frame.
        This is not a blocking call showing the view.
        Your code will continue to run after this call
        and the view will appear in the next dispatch
        of ``on_update``/``on_draw```.

        Calling this function is the same as setting the
        :py:attr:`arcade.Window.current_view` attribute.

        :param new_view: View to show
        """
        if not isinstance(new_view, View):
            raise TypeError(
                f"Window.show_view() takes an arcade.View," f"but it got a {type(new_view)}."
            )

        self._ctx.screen.use()
        self.viewport = (0, 0, self.width, self.height)

        # Store the Window that is showing the "new_view" View.
        if new_view.window is None:
            new_view.window = self
        # NOTE: This is not likely to happen and is creating issues for the test suite.
        # elif new_view.window != self:
        #     raise RuntimeError((
        #         "You are attempting to pass the same view "
        #         "object between multiple windows. A single "
        #         "view object can only be used in one window. "
        #         f"{self} != {new_view.window}"
        #     ))

        # remove previously shown view's handlers
        if self._current_view is not None:
            self._current_view.on_hide_view()
            if self._current_view.has_sections:
                self.remove_handlers(self._current_view.section_manager)
            self.remove_handlers(self._current_view)

        # push new view's handlers
        self._current_view = new_view
        if new_view.has_sections:
            section_manager_managed_events = new_view.section_manager.managed_events
            section_handlers = {
                event_type: getattr(new_view.section_manager, event_type, None)
                for event_type in section_manager_managed_events
            }
            if section_handlers:
                self.push_handlers(**section_handlers)
        else:
            section_manager_managed_events = set()

        # Note: Excluding on_show because this even can trigger multiple times.
        #       It should only be called once when the view is shown.
        view_handlers = {
            event_type: getattr(new_view, event_type, None)
            for event_type in self.event_types
            if event_type != "on_show"
            and event_type not in section_manager_managed_events
            and hasattr(new_view, event_type)
        }
        if view_handlers:
            self.push_handlers(**view_handlers)
        self._current_view.on_show()
        self._current_view.on_show_view()
        if self._current_view.has_sections:
            self._current_view.section_manager.on_show_view()

        # Note: After the View has been pushed onto pyglet's stack of event handlers (via push_handlers()), pyglet
        # will still call the Window's event handlers. (See pyglet's EventDispatcher.dispatch_event() implementation
        # for details)

    def hide_view(self) -> None:
        """
        Hide the currently active view (if any) returning us
        back to ``on_draw`` and ``on_update`` functions in the window.

        This is not necessary to call if you are switching views.
        Simply call ``show_view`` again.
        """
        if self._current_view is None:
            return

        self._current_view.on_hide_view()
        if self._current_view.has_sections:
            self._current_view.section_manager.on_hide_view()
            self.remove_handlers(self._current_view.section_manager)
        self.remove_handlers(self._current_view)
        self._current_view = None

    def _create(self) -> None:
        super()._create()

    def _recreate(self, changes) -> None:
        super()._recreate(changes)

    def flip(self) -> None:
        """
        Window framebuffers normally have a back and front buffer.
        This method makes the back buffer visible and hides the front buffer.
        A frame is rendered into the back buffer, so this method displays
        the frame we currently worked on.

        This method also garbage collect OpenGL resources
        before swapping the buffers.
        """
        # Garbage collect OpenGL resources
        num_collected = self.ctx.gc()
        LOG.debug("Garbage collected %s OpenGL resource(s)", num_collected)

        super().flip()

    def switch_to(self) -> None:
        """Switch the this window."""
        super().switch_to()

    def set_caption(self, caption) -> None:
        """Set the caption for the window."""
        super().set_caption(caption)

    def set_minimum_size(self, width: int, height: int) -> None:
        """Set smallest window size."""
        super().set_minimum_size(width, height)

    def set_maximum_size(self, width, height) -> None:
        """Set largest window size."""
        super().set_maximum_size(width, height)

    def set_location(self, x, y) -> None:
        """Set location of the window."""
        super().set_location(x, y)

    def activate(self) -> None:
        """Activate this window."""
        super().activate()

    def minimize(self) -> None:
        """Minimize the window."""
        super().minimize()

    def maximize(self) -> None:
        """Maximize  the window."""
        super().maximize()

    def set_vsync(self, vsync: bool) -> None:
        """Set if we sync our draws to the monitors vertical sync rate."""
        super().set_vsync(vsync)

    def set_mouse_platform_visible(self, platform_visible=None) -> None:
        """
        .. warning:: You are probably looking for
                     :meth:`~.Window.set_mouse_visible`!

        This method was implemented to prevent PyCharm from displaying
        linter warnings. Most users will never need to set
        platform-specific visibility as the defaults from pyglet will
        usually handle their needs automatically.

        For more information on what this means, see the documentation
        for :py:meth:`pyglet.window.Window.set_mouse_platform_visible`.
        """
        super().set_mouse_platform_visible(platform_visible)

    def set_exclusive_mouse(self, exclusive=True) -> None:
        """Capture the mouse."""
        super().set_exclusive_mouse(exclusive)

    def set_exclusive_keyboard(self, exclusive=True) -> None:
        """Capture all keyboard input."""
        super().set_exclusive_keyboard(exclusive)

    def get_system_mouse_cursor(self, name) -> MouseCursor:
        """Get the system mouse cursor"""
        return super().get_system_mouse_cursor(name)

    def dispatch_events(self) -> None:
        """Dispatch events"""
        super().dispatch_events()

    def on_mouse_enter(self, x: int, y: int) -> Optional[bool]:
        """
        Called once whenever the mouse enters the window area on screen.

        This event will not be triggered if the mouse is currently being
        dragged.

        :param x:
        :param y:
        """
        pass

    def on_mouse_leave(self, x: int, y: int) -> Optional[bool]:
        """
        Called once whenever the mouse leaves the window area on screen.

        This event will not be triggered if the mouse is currently being
        dragged. Note that the coordinates of the mouse pointer will be
        outside of the window rectangle.

        :param x:
        :param y:
        """
        pass

    @property
    def center(self) -> tuple[float, float]:
        """Returns the coordinates of the center of the window."""
        return (self.width / 2, self.height / 2)

    @property
    def center_x(self) -> float:
        """Returns the X-coordinate of the center of the window."""
        return self.width / 2

    @property
    def center_y(self) -> float:
        """Returns the Y-coordinate of the center of the window."""
        return self.height / 2

    # --- CLOCK ALIASES ---
    @property
    def time(self) -> float:
        return self._global_clock.time

    @property
    def fixed_time(self) -> float:
        return self._fixed_clock.time

    @property
    def delta_time(self) -> float:
        return self._global_clock.delta_time

    @property
    def fixed_delta_time(self) -> float:
        return self._fixed_rate

    @property
    def global_clock(self) -> Clock:
        return self._global_clock

    @property
    def global_fixed_clock(self) -> FixedClock:
        return self._fixed_clock

    # Possibly useful clock properties

    # @property
    # def current_fixed_tick(self) -> int:
    #     return self._fixed_clock.ticks

    # @property
    # def accumulated_time(self) -> float:
    #     return self._fixed_clock.accumulated

    # @property
    # def accumulated_fraction(self) -> float:
    #     return self._fixed_clock.fraction


def open_window(
    width: int,
    height: int,
    window_title: Optional[str] = None,
    resizable: bool = False,
    antialiasing: bool = True,
) -> Window:
    """
    This function opens a window. For ease-of-use we assume there will only be one window, and the
    programmer does not need to keep a handle to the window. This isn't the best architecture, because
    the window handle is stored in a global, but it makes things easier for programmers if they don't
    have to track a window pointer.

    :param width: Width of the window.
    :param height: Height of the window.
    :param window_title: Title of the window.
    :param resizable: Whether the user can resize the window.
    :param antialiasing: Smooth the graphics?

    :returns: Handle to window
    """

    global _window
    _window = Window(width, height, window_title, resizable=resizable, antialiasing=antialiasing)
    _window.invalid = False
    return _window


class View:
    """
    Support different views/screens in a window.
    """

    def __init__(self, window: Optional[Window] = None) -> None:
        self.window = arcade.get_window() if window is None else window
        self.key: Optional[int] = None
        self._section_manager: Optional[SectionManager] = None

    @property
    def section_manager(self) -> SectionManager:
        """lazy instantiation of the section manager"""
        if self._section_manager is None:
            self._section_manager = SectionManager(self)
        return self._section_manager

    @property
    def has_sections(self) -> bool:
        """Return if the View has sections"""
        if self._section_manager is None:
            return False
        else:
            return self.section_manager.has_sections

    def add_section(
        self,
        section: arcade.Section,
        at_index: Optional[int] = None,
        at_draw_order: Optional[int] = None,
    ) -> None:
        """
        Adds a section to the view Section Manager.

        :param section: the section to add to this section manager
        :param at_index: inserts the section at that index for event capture and update events. If None at the end
        :param at_draw_order: inserts the section in a specific draw order. Overwrites section.draw_order
        """
        self.section_manager.add_section(section, at_index, at_draw_order)

    def clear(
        self,
        color: Optional[RGBOrA255] = None,
        color_normalized: Optional[RGBANormalized] = None,
        viewport: Optional[tuple[int, int, int, int]] = None,
    ) -> None:
        """Clears the window with the configured background color
        set through :py:attr:`arcade.Window.background_color`.

        :param color: (Optional) override the current background color
            with one of the following:

            1. A :py:class:`~arcade.types.Color` instance
            2. A 3 or 4-length RGB/RGBA :py:class:`tuple` of byte values (0 to 255)

        :param color_normalized: (Optional) override the current background color
            using normalized values (0.0 to 1.0). For example, (1.0, 0.0, 0.0, 1.0)
            making the window contents red.

        :param Tuple[int, int, int, int] viewport: The viewport range to clear
        """
        self.window.clear(color=color, color_normalized=color_normalized, viewport=viewport)

    def on_update(self, delta_time: float) -> Optional[bool]:
        """To be overridden"""
        pass

    def on_fixed_update(self, delta_time: float):
        """To be overridden"""
        pass

    def on_draw(self) -> Optional[bool]:
        """Called when this view should draw"""
        pass

    def on_show(self) -> None:
        """Deprecated. Use :py:meth:`~arcade.View.on_show_view` instead."""
        pass

    def on_show_view(self) -> None:
        """
        Called once when the view is shown.

        .. seealso:: :py:meth:`~arcade.View.on_hide_view`
        """
        pass

    def on_hide_view(self) -> None:
        """Called once when this view is hidden."""
        pass

    def on_mouse_motion(self, x: int, y: int, dx: int, dy: int) -> Optional[bool]:
        """
        Override this function to add mouse functionality.

        :param x: x position of mouse
        :param y: y position of mouse
        :param dx: Change in x since the last time this method was called
        :param dy: Change in y since the last time this method was called
        """
        pass

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> Optional[bool]:
        """
        Override this function to add mouse button functionality.

        :param x: x position of the mouse
        :param y: y position of the mouse
        :param button: What button was hit. One of:
                           arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT,
                           arcade.MOUSE_BUTTON_MIDDLE
        :param modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        pass

    def on_mouse_drag(
        self, x: int, y: int, dx: int, dy: int, _buttons: int, _modifiers: int
    ) -> Optional[bool]:
        """
        Override this function to add mouse button functionality.

        :param x: x position of mouse
        :param y: y position of mouse
        :param dx: Change in x since the last time this method was called
        :param dy: Change in y since the last time this method was called
        :param _buttons: Which button is pressed
        :param _modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        self.on_mouse_motion(x, y, dx, dy)
        return False

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> Optional[bool]:
        """
        Override this function to add mouse button functionality.

        :param x: x position of mouse
        :param y: y position of mouse
        :param button: What button was hit. One of:
                           arcade.MOUSE_BUTTON_LEFT, arcade.MOUSE_BUTTON_RIGHT,
                           arcade.MOUSE_BUTTON_MIDDLE
        :param modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        pass

    def on_mouse_scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> Optional[bool]:
        """
        User moves the scroll wheel.

        :param x: x position of mouse
        :param y: y position of mouse
        :param scroll_x: amount of x pixels scrolled since last call
        :param scroll_y: amount of y pixels scrolled since last call
        """
        pass

    def on_key_press(self, symbol: int, modifiers: int) -> Optional[bool]:
        """
        Override this function to add key press functionality.

        :param symbol: Key that was hit
        :param modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                              active during this event. See :ref:`keyboard_modifiers`.
        """
        try:
            self.key = symbol
        except AttributeError:
            pass

        return False

    def on_key_release(self, _symbol: int, _modifiers: int) -> Optional[bool]:
        """
        Override this function to add key release functionality.

        :param _symbol: Key that was hit
        :param _modifiers: Bitwise 'and' of all modifiers (shift, ctrl, num lock)
                               active during this event. See :ref:`keyboard_modifiers`.
        """
        try:
            self.key = None
        except AttributeError:
            pass

        return False

    def on_resize(self, width: int, height: int) -> Optional[bool]:
        """
        Called when the window is resized while this view is active.
        :py:meth:`~arcade.Window.on_resize` is also called separately.
        By default this method does nothing and can be overridden to
        handle resize logic.
        """
        pass

    def on_mouse_enter(self, x: int, y: int) -> Optional[bool]:
        """
        Called when the mouse was moved into the window.
        This event will not be triggered if the mouse is currently being
        dragged.

        :param x: x position of mouse
        :param y: y position of mouse
        """
        pass

    def on_mouse_leave(self, x: int, y: int) -> Optional[bool]:
        """
        Called when the mouse was moved outside of the window.
        This event will not be triggered if the mouse is currently being
        dragged. Note that the coordinates of the mouse pointer will be
        outside of the window rectangle.

        :param x: x position of mouse
        :param y: y position of mouse
        """
        pass
