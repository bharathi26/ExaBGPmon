from ipaddress import IPv4Network, IPv6Network, AddressValueError
from flask.ext.wtf import Form
from wtforms import StringField, SubmitField, SelectField, PasswordField, TextAreaField, BooleanField
from wtforms.validators import Required, IPAddress, StopValidation, NumberRange, Optional, ValidationError

def validate_prefix(form, field):
    try:
        IPv4Network(unicode(field.data))
    except AddressValueError:
        raise ValidationError('%s is not a valid prefix' % field.data)
    except ValueError as e:
        raise ValidationError(e.message)

class Range(object):
    """ This replaces wtforms NumberRange() validator since it wasn't working correctly"""

    def __init__(self, min=-1, max=-1, message=None):
        self.min = min
        self.max = max
        if not message:
            message = u'Must be a number between %i and %i characters long.' % (min, max)
        self.message = message

    def __call__(self, form, field):
        n = field.data
        try:
            if not int(self.min) < int(n) < int(self.max):
                raise ValidationError(self.message)
        except TypeError:
            raise ValidationError(self.message)


class AdvertiseRoute(Form):

    prefix = StringField('IP Prefix', validators=[Required(), validate_prefix])
    next_hop = StringField('Next Hop', validators=[Required(), IPAddress()])
    med = StringField('MED', validators=[Optional(), Range(0, 500)])
    local_pref = StringField('Local Preference', validators=[Optional(), Range(0, 500)])
    origin = SelectField('Origin', choices=[('igp','IGP'),('egp', 'EGP'), ('?', 'Incomplete (?)')], default='?', validators=[Required()])
    submit = SubmitField('Send')

    def validate_prefix(form, field):
        try:
            IPv4Network(unicode(field.data))
        except AddressValueError:
            raise ValidationError('%s is not a valid prefix' % field.data)
        except ValueError as e:
            raise ValidationError(e.message)

class ConfigForm(Form):

    router_id = StringField('Router-ID', validators=[Required(), IPAddress()])
    asn = StringField('Local AS Number', validators=[Required(), Range(1, 65535)])
    local_ip = StringField('Local IP Address', validators=[Required(), IPAddress()])
    submit = SubmitField('Save Config')

class BGPPeer(Form):

    ip_address = StringField('IP Address', validators=[Required(), IPAddress()])
    asn = StringField('AS Number', validators=[Required(), Range(1, 65535)])
    enabled = BooleanField('Enabled')
    submit = SubmitField('Save')    submit = SubmitField('Save')