from flask_wtf import FlaskForm
from wtforms import SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired

class OrderForm(FlaskForm):
    inventory_item = SelectField('Inventory Item', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Add to Order')