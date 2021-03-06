# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# from flask import url_for
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from app.home.models import Workflow  # noqa, flake8 issue
from hashlib import md5  # avatar hash
import base64  # api token
import os

import datetime


class User(db.Model, UserMixin):

    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, index=True)
    email = Column(String(120), unique=True, index=True)
    password_hash = Column(String(128))
    remember_me = Column(Boolean, default=False)
    confirmed = Column(Boolean, default=False)
    registered_on = Column(DateTime, index=True, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    token = Column(String(32), index=True, unique=True)
    token_expiration = Column(db.DateTime)

    # Relationships
    workflows = relationship("Workflow", backref="user", lazy="dynamic")

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, "__iter__") and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == "password":
                self.set_password(value)

            setattr(self, property, value)

    def __repr__(self):
        return str(self.to_dict())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        return "https://www.gravatar.com/avatar/{}?d=identicon&s={}".format(
            digest, size
        )

    def to_dict(self, include_email=False):
        data = {
            "id": self.id,
            "username": self.username,
            "registered_on": self.registered_on,
            "_links": {
                # 'self': url_for('blueprint_api.get_user', id=self.id),
                "avatar": self.avatar(128)
            },
        }
        if include_email:
            data["email"] = self.email
        return data

    def get_token(self, expires_in=86400):
        now = datetime.datetime.utcnow()
        if self.token and self.token_expiration > now + datetime.timedelta(seconds=60):
            return self.token
        self.token = base64.b64encode(os.urandom(24)).decode("utf-8")
        self.token_expiration = now + datetime.timedelta(seconds=expires_in)
        db.session.add(self)
        return self.token

    def revoke_token(self):
        self.token_expiration = datetime.datetime.utcnow() - datetime.timedelta(
            seconds=1
        )

    @staticmethod
    def check_token(token):
        user = User.query.filter_by(token=token).first()
        if user is None or user.token_expiration < datetime.datetime.utcnow():
            return None
        return user


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@login_manager.request_loader
def request_loader(request):
    username = request.form.get("username")
    user = User.query.filter_by(username=username).first()
    return user if user else None
