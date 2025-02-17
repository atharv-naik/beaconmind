#!/bin/sh

export PGUSER="postgres"

psql -c "CREATE DATABASE afmwdb;"
