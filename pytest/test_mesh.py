#!/usr/bin/env python
# coding: utf-8
"""Tests for the mesh submodule: definition and transformation of base meshes."""

import pytest

import numpy as np

from capytaine.mesh.mesh import Mesh
from capytaine.tools.geometry import Plane, xOz_Plane
from capytaine.geometric_bodies import HorizontalCylinder, Sphere

# Some meshes that will be used in the following tests.
test_mesh = Mesh(vertices=np.random.rand(4, 3), faces=[range(4)], name="test_mesh")
cylinder = HorizontalCylinder().mesh.merge()
sphere = Sphere(radius=1).mesh.merge()


def test_mesh_initialization():
    """Test how the code checks the validity of the parameters."""
    with pytest.raises(AssertionError):
        Mesh(vertices=np.random.rand(6, 3), faces=[(0, 1, 2), (3, 4, 5)])

    with pytest.raises(AssertionError):
        Mesh(vertices=np.random.rand(4, 3), faces=[(0, 1, 2, np.pi)])

    with pytest.raises(AssertionError):
        Mesh(vertices=np.random.rand(3, 3), faces=[(0, 1, 2, 3)])


def test_vertices_and_faces_get_and_set():
    """Test get and set functions for vertices and faces."""
    # Get faces
    faces = cylinder.faces
    vertices = cylinder.vertices

    new_cylinder = Mesh(name="new_cylinder")

    # Set faces
    with pytest.raises(AssertionError):
        new_cylinder.faces = faces
        # You should set the vertices first.
    new_cylinder.vertices = vertices
    new_cylinder.faces = faces

    assert new_cylinder == cylinder


def test_mesh_naming():
    """Test how the mesh handle names and string representation."""
    # Test string representation
    assert str(test_mesh) == 'test_mesh'  # Just the name
    assert repr(test_mesh) == "Mesh(nb_vertices=4, nb_faces=1, name=test_mesh)"  # A longer representation.

    # Test automatic naming
    dummy_mesh = Mesh()  # Automatically named something like mesh_1
    other_dummy_mesh = Mesh()  # Automatically named something like mesh_2
    assert dummy_mesh.name[:5] == "mesh_"
    assert other_dummy_mesh.name[:5] == "mesh_"
    assert int(dummy_mesh.name[5:]) + 1 == int(other_dummy_mesh.name[5:])


def test_set_of_faces():
    """Test the representation of the mesh as a set of faces.
    Also allows to define the equality of two meshes."""
    faces = cylinder.as_set_of_faces()
    assert isinstance(faces, frozenset)
    assert len(faces) == cylinder.nb_faces
    assert all(len(face) == 4 or len(face) == 3 for face in faces)  # Each face is represented by 3 or 4 points
    assert all(len(vertex) == 3 for face in faces for vertex in face)  # Each point is represented by 3 coordinates.

    assert cylinder == cylinder  # The equality is defined as the equality of the set of faces.
    assert Mesh.from_set_of_faces(faces) == cylinder  # The mesh can be reconstructed from a set of faces.


def test_copy():
    """Test the copy and renaming of meshes."""
    assert test_mesh.copy() is not test_mesh
    assert test_mesh.copy() == test_mesh
    assert test_mesh.copy(name="copy_of_the_test_mesh").name == "copy_of_the_test_mesh"
    assert test_mesh.merge() is test_mesh


def test_shape_helper_functions():
    assert np.allclose(sphere.center_of_mass_of_nodes, (0.0, 0.0, 0.0))
    assert np.isclose(sphere.diameter_of_nodes, 2.0)
    assert cylinder.squared_axis_aligned_bbox == (-5.0, 5.0, -5.0, 5.0, -5.0, 5.0)


def test_translate():
    assert cylinder.translated_x(0) == cylinder
    assert cylinder.translated_y(0) == cylinder
    assert cylinder.translated_z(0) == cylinder
    assert cylinder.translated([0, 0, 0]) == cylinder

    translated_sphere = sphere.translated([1, 2, 3])
    assert np.allclose(translated_sphere.center_of_mass_of_nodes, (1.0, 2.0, 3.0))
    assert translated_sphere.diameter_of_nodes == sphere.diameter_of_nodes


def test_rotate():
    assert cylinder.rotated_x(0.0) == cylinder
    assert cylinder.rotated_y(0.0) == cylinder
    assert cylinder.rotated_z(0.0) == cylinder

    new_cylinder = cylinder.rotated_z(np.pi/2)
    assert np.allclose(new_cylinder.center_of_mass_of_nodes, cylinder.center_of_mass_of_nodes)
    assert new_cylinder.squared_axis_aligned_bbox == (-5.0, 5.0, -5.0, 5.0, -5.0, 5.0)


def test_mirror():
    new_cylinder = cylinder.mirrored(Plane())
    cylinder.mirror(Plane())
    assert new_cylinder == cylinder


def test_symmetrized():
    from capytaine.mesh.symmetries import ReflectionSymmetry
    sym = cylinder.merge().symmetrized(xOz_Plane)
    assert isinstance(sym, ReflectionSymmetry)


def test_mesh_quality():
    # TODO: Could be improved...
    cylinder.triangulate_quadrangles()
    cylinder.merge_duplicates(atol=1e-5)
    cylinder.heal_mesh()


def test_clipper():
    """Test clipping of mesh."""
    mesh = Sphere(radius=5.0, ntheta=10).mesh.merge()
    aabb = mesh.axis_aligned_bbox

    mesh.keep_immersed_part(free_surface=0.0, sea_bottom=-np.infty)
    assert np.allclose(mesh.axis_aligned_bbox, aabb[:5] + (0,))  # the last item of the tuple has changed

    mesh.keep_immersed_part(free_surface=0.0, sea_bottom=-1.0)
    assert np.allclose(mesh.axis_aligned_bbox, aabb[:4] + (-1, 0,))  # the last item of the tuple has changed

    # With CollectionOfMeshes (AxialSymmetry)
    mesh = Sphere(radius=5.0, ntheta=10).mesh
    aabb = mesh.merge().axis_aligned_bbox

    mesh.keep_immersed_part(free_surface=0.0, sea_bottom=-np.infty)
    assert np.allclose(mesh.merge().axis_aligned_bbox, aabb[:5] + (0,))  # the last item of the tuple has changed

    mesh.keep_immersed_part(free_surface=0.0, sea_bottom=-1.0)
    assert np.allclose(mesh.merge().axis_aligned_bbox, aabb[:4] + (-1, 0,))  # the last item of the tuple has changed


def test_clipper_corner_cases():
    mesh = sphere.translated_z(10.0)

    plane = Plane(point=(0, 0, 0), normal=(0, 0, 1))
    clipped_mesh = mesh.clip(plane, inplace=False)
    assert clipped_mesh == Mesh(None, None)  # Empty mesh

    plane = Plane(point=(0, 0, 0), normal=(0, 0, -1))
    clipped_mesh = mesh.clip(plane, inplace=False)
    assert clipped_mesh == mesh  # Unchanged mesh

    # Two distinct bodies
    two_spheres = Mesh.join_meshes(sphere.translated_z(10.0), sphere.translated_z(-10.0))
    plane = Plane(point=(0, 0, 0), normal=(0, 0, -1))
    one_sphere_remaining = two_spheres.clip(plane, inplace=False)
    assert one_sphere_remaining == sphere.translated_z(10.0)
