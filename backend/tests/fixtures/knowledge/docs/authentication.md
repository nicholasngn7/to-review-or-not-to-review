# Authentication and OAuth tokens

This document describes how user authentication works in the system. It covers the
login flow, OAuth authorization, session cookies, and access token refresh.

## Login flow

A user submits credentials to the login endpoint. On success the server issues a
short-lived access token and a longer-lived refresh token. The access token is sent
on every authenticated request.

## OAuth authorization

The OAuth authorization code flow exchanges an authorization code for an access token.
Clients must store the refresh token securely and rotate credentials regularly. Never
log raw tokens or passwords.
