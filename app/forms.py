from ipaddress import IPv4Network, IPv6Network, AddressValueError
from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, SelectField, PasswordField, TextAreaField, BooleanField
from wtforms.validators import Required, IPAddress, StopValidation, Email, EqualTo, NumberRange, Optional, ValidationError

def validate_prefix(form, field):
    try:
        IPv4Network(unicode(field.data))
    except AddressValueError:
        raise ValidationError('%s is not a valid prefix' % field.data)
    except ValueError as e:
        raise ValidationError(e.message)

class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):
        pass

class AdvertiseRoute(Form):

    prefix = StringField('IP Prefix', validators=[Required(), validate_prefix])
    next_hop = StringField('Next Hop', validators=[Required(), IPAddress()])
    med = StringField('MED', validators=[Optional(), NumberRange(0, 500, 'Must be between 0 and 500')])
    local_pref = StringField('Local Preference', validators=[Optional(), NumberRange(0, 500, 'Must be between 0 and 255')])
    origin = SelectField('Origin', choices=[('igp','IGP'),('egp', 'EGP'), ('?', 'Incomplete (?)')], default='?', validators=[Required()])
    submit = SubmitField('Send')

    def validate_prefix(form, field):
        try:
            IPv4Network(unicode(field.data))
        except AddressValueError:
            raise ValidationError('%s is not a valid prefix' % field.data)
        except ValueError as e:
            raise ValidationError(e.message)