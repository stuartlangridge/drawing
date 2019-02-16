# tool_line.py

from gi.repository import Gtk, Gdk
import cairo, math

from .tools import ToolTemplate

class ToolLine(ToolTemplate):
	__gtype_name__ = 'ToolLine'

	implements_panel = False

	def __init__(self, window, **kwargs):
		super().__init__('line', _("Line"), 'list-remove-symbolic', window, False)
		self.use_size = True

		self.add_tool_action_enum('line_shape', 'round')
		self.add_tool_action_boolean('use_dashes', False)
		self.add_tool_action_boolean('is_arrow', False)
		self.add_tool_action_enum('cairo_operator', 'over')

		# Default values
		self.selected_shape_label = _("Round")
		self.selected_operator = cairo.Operator.OVER
		self.selected_end_id = cairo.LineCap.ROUND
		self.wait_points = (-1.0, -1.0, -1.0, -1.0)
		self.use_dashes = False
		self.use_arrow = False

	def set_active_shape(self):
		if self.get_option_value('line_shape') == 'square':
			self.selected_end_id = cairo.LineCap.BUTT
			self.selected_shape_label = _("Square")
		else:
			self.selected_end_id = cairo.LineCap.ROUND
			self.selected_shape_label = _("Round")

	def set_active_operator(self):
		state_as_string = self.get_option_value('cairo_operator')
		if state_as_string == 'difference':
			self.selected_operator = cairo.Operator.DIFFERENCE
			self.selected_operator_label = _("Difference")
		elif state_as_string == 'exclusion':
			self.selected_operator = cairo.Operator.EXCLUSION
			self.selected_operator_label = _("Exclusion")
		elif state_as_string == 'clear':
			self.selected_operator = cairo.Operator.CLEAR
			self.selected_operator_label = _("Eraser")
		else:
			self.selected_operator = cairo.Operator.OVER
			self.selected_operator_label = _("Classic")

	def get_options_model(self):
		builder = Gtk.Builder.new_from_resource('/com/github/maoschanz/Drawing/tools/ui/tool_line.ui')
		return builder.get_object('options-menu')

	def get_options_label(self):
		return _("Line options")

	def get_edition_status(self): # TODO l'opérateur est important
		label = self.label + ' (' + self.selected_shape_label + ') '
		if self.use_arrow and self.use_dashes:
			label = label + ' - ' + _("Arrow") + ' - ' + _("With dashes")
		elif self.use_arrow:
			label = label + ' - ' + _("Arrow")
		elif self.use_dashes:
			label = label + ' - ' + _("With dashes")
		return label

	def give_back_control(self):
		if self.wait_points == (-1.0, -1.0, -1.0, -1.0):
			self.x_press = 0.0
			self.y_press = 0.0
			return False
		else:
			self.wait_points = (-1.0, -1.0, -1.0, -1.0)
			self.x_press = 0.0
			self.y_press = 0.0
			return True

	def on_motion_on_area(self, area, event, surface, event_x, event_y):
		self.restore_pixbuf()
		w_context = cairo.Context(self.get_surface())
		w_context.move_to(self.x_press, self.y_press)
		w_context.line_to(event_x, event_y)

		self._path = w_context.copy_path()
		operation = self.build_operation(event_x, event_y)
		self.do_tool_operation(operation)

	def on_press_on_area(self, area, event, surface, tool_width, left_color, right_color, event_x, event_y):
		self.x_press = event_x
		self.y_press = event_y
		self.tool_width = tool_width
		if event.button == 1:
			self.main_color = left_color
		if event.button == 3:
			self.main_color = right_color
		self.use_dashes = self.get_option_value('use_dashes')
		self.use_arrow = self.get_option_value('is_arrow')
		self.set_active_shape()
		self.set_active_operator()

	def on_release_on_area(self, area, event, surface, event_x, event_y):
		self.restore_pixbuf()
		w_context = cairo.Context(self.get_surface())
		w_context.move_to(self.x_press, self.y_press)
		w_context.line_to(event_x, event_y)

		self._path = w_context.copy_path()
		operation = self.build_operation(event_x, event_y)
		self.apply_operation(operation)
		self.x_press = 0.0
		self.y_press = 0.0

	def add_arrow_triangle(self, w_context, x_release, y_release, x_press, y_press, line_width):
		w_context.new_path()
		w_context.set_line_width(line_width)
		w_context.set_dash([1, 0])
		w_context.move_to(x_release, y_release)
		x_length = max(x_press, x_release) - min(x_press, x_release)
		y_length = max(y_press, y_release) - min(y_press, y_release)
		line_length = math.sqrt( (x_length)**2 + (y_length)**2 )
		arrow_width = math.log(line_length)
		if (x_press - x_release) != 0:
			delta = (y_press - y_release) / (x_press - x_release)
		else:
			delta = 1.0

		x_backpoint = (x_press + x_release)/2
		y_backpoint = (y_press + y_release)/2
		i = 0
		while i < arrow_width:
			i = i + 2
			x_backpoint = (x_backpoint + x_release)/2
			y_backpoint = (y_backpoint + y_release)/2

		if delta < -1.5 or delta > 1.0:
			w_context.line_to(x_backpoint-arrow_width, y_backpoint)
			w_context.line_to(x_backpoint+arrow_width, y_backpoint)
		elif delta > -0.5 and delta <= 1.0:
			w_context.line_to(x_backpoint, y_backpoint-arrow_width)
			w_context.line_to(x_backpoint, y_backpoint+arrow_width)
		else:
			w_context.line_to(x_backpoint-arrow_width, y_backpoint-arrow_width)
			w_context.line_to(x_backpoint+arrow_width, y_backpoint+arrow_width)

		w_context.close_path()
		w_context.fill_preserve()
		w_context.stroke()

	def build_operation(self, event_x, event_y):
		operation = {
			'tool_id': self.id,
			'rgba': self.main_color,
			'operator': self.selected_operator,
			'line_width': self.tool_width,
			'line_cap': self.selected_end_id,
			'use_dashes': self.use_dashes,
			'use_arrow': self.use_arrow,
			'path': self._path,
			'x_release': event_x,
			'y_release': event_y,
			'x_press': self.x_press,
			'y_press': self.y_press
		}
		return operation

	def do_tool_operation(self, operation):
		if operation['tool_id'] != self.id:
			return
		self.restore_pixbuf()
		w_context = cairo.Context(self.get_surface())
		w_context.set_operator(operation['operator'])
		w_context.set_line_cap(operation['line_cap'])
		#w_context.set_line_join(operation['line_join'])
		line_width = operation['line_width']
		w_context.set_line_width(line_width)
		rgba = operation['rgba']
		w_context.set_source_rgba(rgba.red, rgba.green, rgba.blue, rgba.alpha)
		if operation['use_dashes']:
			w_context.set_dash([2*line_width, 2*line_width])
		w_context.append_path(operation['path'])
		w_context.stroke()

		if operation['use_arrow']:
			x_press = operation['x_press']
			y_press = operation['y_press']
			x_release = operation['x_release']
			y_release = operation['y_release']
			self.add_arrow_triangle(w_context, x_release, y_release, x_press, y_press, line_width)
