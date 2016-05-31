#pragma once

#include <boost/range/iterator_range.hpp>

#include "exception.cpp"
#include "numpy_boost/ndarray.cpp"
#include "opcode/Opcode.h"


template<typename real_t, typename index_t>
class MeshModel {
    /* simple wrapper class for vertices and triangles, and corresponding opcode-model */
public:
    const ndarray<real_t, 2>    vertices;
    const ndarray<index_t, 2>   triangles;
    const Opcode::MeshInterface interface;
	const Opcode::Model         model;

    Mesh(const ndarray<real_t, 2> vertices, const ndarray<index_t, 2> triangles) :
        vertices    (vertices),
        triangles   (triangles),
        interface   (init_interface()),
        model       (init_model())
    {}

private:
    Opcode::MeshInterface init_interface() const {
        Opcode::MeshInterface interface;
        interface.SetNbTriangles(triangles.size());
        interface.SetNbVertices(vertices.size());
        // this casting implicitly validates the input shapes and strides
        interface.SetPointers(
            triangles.view<IceMaths::IndexedTriangle>().data(),
            vertices .view<IceMaths::Point          >().data()
        );
        return interface;
    }

    Opcode::Model init_model() const {
        //Tree building settings
        Opcode::OPCODECREATE OPCC;
        OPCC.mIMesh = &interface;
        OPCC.mNoLeaf = true;
        OPCC.mQuantized = false;
        OPCC.mKeepOriginal = false;

        Opcode::Model model;
        model.Build(OPCC);
        return model;
    }
};


template<typename real_t, typename index_t>
class MeshCollision {
    typedef Mesh<real_t, index_t> mesh_t;
    typedef ndarray<real_t, 2> affine_t;

	const mesh_t mesh0;
	const mesh_t mesh1;

public:
    MeshCollision(const mesh_t mesh0, const mesh_t mesh1) :
        mesh0(mesh0), mesh1(mesh1),
    {}

    ndarray<index_t, 2> query(const affine_t affine0, const affine_t affine1) const {
        // helper object to pass arguments to collision query
		Opcode::BVTCache ColCache;
		ColCache.Model0 = &mesh0.model;
		ColCache.Model1 = &mesh1.model;

		// Collision query
    	Opcode::AABBTreeCollider TC;
		const bool IsOk(
		    TC.Collide(
		        ColCache,
		        (IceMaths::Matrix4x4*)affine0.data(),
		        (IceMaths::Matrix4x4*)affine1.data()
		    )
		);

        // wrap resulting pairs in numpy array
		const bool Status (TC.GetContactStatus());
		boost::iterator_range<IceCore::Pair*> pairs = (Status > 0) ?
            boost::make_iterator_range(TC.GetPairs(), TC.GetPairs() + TC.GetNbPairs()) :
            boost::make_iterator_range(0, 0);

		return ndarray_from_range(pairs).unview<index_t>();
    }

};