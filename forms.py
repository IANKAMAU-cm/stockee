from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, IntegerField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import SelectField

class OrderForm(FlaskForm):
    inventory_item = SelectField('Inventory Item', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Add to Order')

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    price = DecimalField('Price', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    unit = SelectField('Unit', choices=[('litres', 'litres'), ('kilograms', 'kilograms'), ('grams', 'grams'), ('milligrams', 'milligrams'), ('millilitre', 'millilitre')], validators=[DataRequired()])
    stock = IntegerField('Stock', validators=[DataRequired()])
    image = FileField('Product Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    submit = SubmitField('Submit')